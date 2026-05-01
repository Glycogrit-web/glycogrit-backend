#!/bin/bash
# Test runner script for GlycoGrit Backend
# Run this before every deployment!

set -e  # Exit on any error

echo "=================================="
echo "🧪 GlycoGrit Backend Test Suite"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found! Installing test dependencies...${NC}"
    pip install -r requirements-test.txt
fi

# Run critical financial tests first
echo -e "${YELLOW}💰 Running CRITICAL Financial Tests...${NC}"
if pytest tests/ -v -m financial --tb=short; then
    echo -e "${GREEN}✅ Financial tests PASSED${NC}"
else
    echo -e "${RED}❌ CRITICAL: Financial tests FAILED!${NC}"
    echo -e "${RED}DO NOT DEPLOY! Fix financial tests first.${NC}"
    exit 1
fi

echo ""

# Run critical security tests
echo -e "${YELLOW}🔒 Running CRITICAL Security Tests...${NC}"
if pytest tests/ -v -m security --tb=short; then
    echo -e "${GREEN}✅ Security tests PASSED${NC}"
else
    echo -e "${RED}❌ CRITICAL: Security tests FAILED!${NC}"
    echo -e "${RED}DO NOT DEPLOY! Fix security tests first.${NC}"
    exit 1
fi

echo ""

# Run all unit tests
echo -e "${YELLOW}🧪 Running Unit Tests...${NC}"
if pytest tests/unit/ -v --tb=short; then
    echo -e "${GREEN}✅ Unit tests PASSED${NC}"
else
    echo -e "${RED}❌ Unit tests FAILED${NC}"
    exit 1
fi

echo ""

# Run integration tests
echo -e "${YELLOW}🔗 Running Integration Tests...${NC}"
if pytest tests/integration/ -v --tb=short; then
    echo -e "${GREEN}✅ Integration tests PASSED${NC}"
else
    echo -e "${RED}❌ Integration tests FAILED${NC}"
    exit 1
fi

echo ""

# Generate coverage report
echo -e "${YELLOW}📊 Generating Coverage Report...${NC}"
pytest --cov=app --cov-report=term --cov-report=html

echo ""
echo "=================================="
echo -e "${GREEN}✅ All tests PASSED!${NC}"
echo "=================================="
echo ""
echo "Coverage report generated in htmlcov/index.html"
echo ""
echo -e "${GREEN}✅ Safe to deploy!${NC}"
