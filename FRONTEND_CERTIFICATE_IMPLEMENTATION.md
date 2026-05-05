# Frontend Certificate Implementation Guide

**Date:** May 5, 2026
**Status:** Implementation Ready
**Backend API:** ✅ Complete and Deployed

---

## Summary

The backend certificate API is fully implemented and deployed. This document provides the complete frontend implementation guide for integrating certificate downloads into the React/TypeScript frontend.

---

## ✅ Already Completed (Backend)

- [x] Certificate generation API endpoints
- [x] Download tracking and limits
- [x] Admin management endpoints
- [x] Database schema
- [x] Complete testing
- [x] Documentation

---

## 🎯 Frontend Changes Required

### 1. TypeScript Types ✅ DONE

**File:** `src/types/reward.ts`

Added certificate-specific fields to `UserReward` interface:
```typescript
// Certificate-specific fields
certificate_url?: string;
certificate_number?: string;
download_count?: number;
download_limit?: number;
last_downloaded_at?: string;
```

Added new interfaces:
- `CertificateResponse`
- `CertificateListItem`
- `CertificateListResponse`
- `DownloadAnalyticsResponse`
- `UpdateDownloadLimitRequest`
- `UpdateEventDefaultLimitRequest`
- `ResetDownloadResponse`

Added helper functions:
- `isCertificate()`
- `canDownloadCertificate()`
- `getRemainingDownloads()`
- `isUnlimitedDownloads()`
- `formatCertificateNumber()`
- `getDownloadStatusColor()`
- `getDownloadStatusLabel()`

### 2. API Client ✅ DONE

**File:** `src/lib/certificates-api.ts`

Created complete API client with:

**User Endpoints:**
- `previewCertificate()` - Preview without tracking
- `downloadCertificate()` - Download with tracking
- `getMyCertificates()` - List all user certificates
- `bulkDownloadCertificates()` - Bulk download

**Admin Endpoints:**
- `updateCertificateDownloadLimit()` - Update individual limit
- `resetCertificateDownloadCount()` - Reset count
- `updateEventDefaultDownloadLimit()` - Set event-wide defaults
- `getDownloadAnalytics()` - View analytics

**Helper Functions:**
- `openCertificate()` - Open in new tab
- `downloadAndOpenCertificate()` - Combined action
- `formatDownloadStats()` - Format for display
- `getDownloadStatusColorClass()` - Tailwind classes
- And 10+ more helper functions

### 3. React Components (TODO)

#### A. User Components

##### **CertificateDownloadButton.tsx**

Purpose: Button component for downloading certificates

```tsx
/**
 * CertificateDownloadButton Component
 * Displays download button with progress indicator
 */

import React, { useState } from 'react';
import { downloadAndOpenCertificate } from '../../lib/certificates-api';
import { UserReward, canDownloadCertificate, getRemainingDownloads } from '../../types/reward';
import { toast } from 'react-hot-toast';

interface CertificateDownloadButtonProps {
  registration_id: number;
  reward?: UserReward;
  onDownloadSuccess?: () => void;
  className?: string;
}

export const CertificateDownloadButton: React.FC<CertificateDownloadButtonProps> = ({
  registration_id,
  reward,
  onDownloadSuccess,
  className = '',
}) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const canDownload = reward ? canDownloadCertificate(reward) : true;
  const remaining = reward ? getRemainingDownloads(reward) : null;

  const handleDownload = async () => {
    setIsDownloading(true);

    try {
      await downloadAndOpenCertificate(registration_id);

      toast.success(
        remaining !== null
          ? `Certificate downloaded! ${remaining - 1} downloads remaining.`
          : 'Certificate downloaded successfully!'
      );

      if (onDownloadSuccess) onDownloadSuccess();
    } catch (error: any) {
      if (error.status === 429) {
        toast.error('Download limit exceeded. Please contact support for more downloads.');
      } else {
        toast.error('Failed to download certificate. Please try again.');
      }
    } finally {
      setIsDownloading(false);
    }
  };

  if (!canDownload) {
    return (
      <button
        disabled
        className={`px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed ${className}`}
      >
        Limit Reached
      </button>
    );
  }

  return (
    <button
      onClick={handleDownload}
      disabled={isDownloading}
      className={`px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${className}`}
    >
      {isDownloading ? (
        <>
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>Downloading...</span>
        </>
      ) : (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Download Certificate</span>
        </>
      )}
    </button>
  );
};
```

##### **CertificateCard.tsx**

Purpose: Display certificate with download stats

```tsx
/**
 * CertificateCard Component
 * Displays certificate details with download tracking
 */

import React from 'react';
import { CertificateListItem } from '../../types/reward';
import { formatDownloadStats } from '../../lib/certificates-api';
import { CertificateDownloadButton } from './CertificateDownloadButton';
import Card from '../common/Card';
import Badge from '../common/Badge';

interface CertificateCardProps {
  certificate: CertificateListItem;
  onRefresh?: () => void;
}

export const CertificateCard: React.FC<CertificateCardProps> = ({
  certificate,
  onRefresh,
}) => {
  const downloadStats = formatDownloadStats(
    certificate.download_count,
    certificate.download_limit
  );

  return (
    <Card className="hover:shadow-lg transition-all">
      <div className="flex flex-col h-full p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-4xl">📜</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {certificate.event_name}
              </h3>
              <p className="text-sm text-gray-500">
                {new Date(certificate.event_date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
          </div>
          {certificate.is_unlimited && (
            <Badge color="green">Unlimited</Badge>
          )}
        </div>

        {/* Certificate Number */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Certificate Number</p>
          <p className="text-sm font-mono text-gray-700">{certificate.certificate_number}</p>
        </div>

        {/* Download Stats */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">Downloads</span>
            <span className={`text-sm font-medium ${downloadStats.color === 'green' ? 'text-green-600' : downloadStats.color === 'red' ? 'text-red-600' : 'text-orange-600'}`}>
              {downloadStats.text}
            </span>
          </div>
          {certificate.download_limit > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${downloadStats.color === 'green' ? 'bg-green-500' : downloadStats.color === 'red' ? 'bg-red-500' : 'bg-orange-500'}`}
                style={{ width: `${Math.min(100, downloadStats.percentage)}%` }}
              />
            </div>
          )}
        </div>

        {/* Last Downloaded */}
        {certificate.last_downloaded_at && (
          <p className="text-xs text-gray-500 mb-4">
            Last downloaded: {new Date(certificate.last_downloaded_at).toLocaleString()}
          </p>
        )}

        {/* Download Button */}
        <div className="mt-auto">
          <CertificateDownloadButton
            registration_id={certificate.registration_id}
            reward={{
              certificate_url: certificate.certificate_url,
              download_count: certificate.download_count,
              download_limit: certificate.download_limit,
            } as any}
            onDownloadSuccess={onRefresh}
            className="w-full"
          />
        </div>
      </div>
    </Card>
  );
};
```

##### **MyCertificatesPage.tsx**

Purpose: User's certificate collection page

```tsx
/**
 * MyCertificatesPage Component
 * Displays all user certificates with download functionality
 */

import React, { useEffect, useState } from 'react';
import { getMyCertificates } from '../../lib/certificates-api';
import { CertificateListResponse } from '../../types/reward';
import { CertificateCard } from '../features/CertificateCard';
import { toast } from 'react-hot-toast';

export const MyCertificatesPage: React.FC = () => {
  const [certificates, setCertificates] = useState<CertificateListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadCertificates = async () => {
    setIsLoading(true);
    try {
      const data = await getMyCertificates();
      setCertificates(data);
    } catch (error) {
      toast.error('Failed to load certificates');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCertificates();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <svg className="animate-spin h-12 w-12 text-blue-600 mx-auto mb-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-600">Loading your certificates...</p>
        </div>
      </div>
    );
  }

  if (!certificates || certificates.total_certificates === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="text-center">
          <span className="text-6xl mb-4 block">📜</span>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Certificates Yet</h2>
          <p className="text-gray-600 mb-6">
            Complete races to earn certificates!
          </p>
          <a
            href="/challenges"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Browse Challenges
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">My Certificates</h1>
        <p className="text-gray-600">
          You have earned {certificates.total_certificates} certificate{certificates.total_certificates !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Certificate Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {certificates.certificates.map((cert) => (
          <CertificateCard
            key={cert.registration_id}
            certificate={cert}
            onRefresh={loadCertificates}
          />
        ))}
      </div>
    </div>
  );
};
```

#### B. Admin Components

##### **CertificateAnalyticsDashboard.tsx**

Purpose: Admin analytics for certificate downloads

```tsx
/**
 * CertificateAnalyticsDashboard Component
 * Admin dashboard for certificate download analytics
 */

import React, { useEffect, useState } from 'react';
import { getDownloadAnalytics } from '../../lib/certificates-api';
import { DownloadAnalyticsResponse } from '../../types/reward';
import { formatBandwidth, formatPercentage } from '../../lib/certificates-api';
import Card from '../common/Card';

interface Props {
  eventId?: number;
}

export const CertificateAnalyticsDashboard: React.FC<Props> = ({ eventId }) => {
  const [analytics, setAnalytics] = useState<DownloadAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadAnalytics = async () => {
      setIsLoading(true);
      try {
        const data = await getDownloadAnalytics(eventId ? { event_id: eventId } : undefined);
        setAnalytics(data);
      } catch (error) {
        console.error('Failed to load analytics:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadAnalytics();
  }, [eventId]);

  if (isLoading || !analytics) {
    return <div>Loading analytics...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Certificate Analytics</h2>
        {analytics.event_name && (
          <p className="text-gray-600">Event: {analytics.event_name}</p>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="p-6">
            <p className="text-sm text-gray-600 mb-1">Total Certificates</p>
            <p className="text-3xl font-bold text-gray-900">{analytics.certificates_generated}</p>
            <p className="text-xs text-gray-500 mt-1">
              of {analytics.completed_activities} completed
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <p className="text-sm text-gray-600 mb-1">Total Downloads</p>
            <p className="text-3xl font-bold text-gray-900">{analytics.total_downloads}</p>
            <p className="text-xs text-gray-500 mt-1">
              Avg: {analytics.average_downloads_per_certificate.toFixed(1)} per certificate
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <p className="text-sm text-gray-600 mb-1">At Limit</p>
            <p className="text-3xl font-bold text-red-600">{analytics.certificates_at_limit}</p>
            <p className="text-xs text-gray-500 mt-1">
              {formatPercentage(analytics.certificates_at_limit_percentage)} of total
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <p className="text-sm text-gray-600 mb-1">Bandwidth Used</p>
            <p className="text-3xl font-bold text-gray-900">
              {formatBandwidth(analytics.bandwidth_used_mb)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Cost: {analytics.estimated_monthly_cost}
            </p>
          </div>
        </Card>
      </div>

      {/* Download Distribution */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Download Distribution</h3>
          <div className="space-y-2">
            {Object.entries(analytics.download_distribution).map(([range, count]) => (
              <div key={range} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{range} downloads</span>
                <div className="flex items-center gap-3">
                  <div className="w-64 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{
                        width: `${(count / analytics.certificates_generated) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-900 w-12 text-right">
                    {count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Top Downloaders */}
      {analytics.top_downloaders && analytics.top_downloaders.length > 0 && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Downloaders</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Participant
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Certificate #
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Downloads
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Last Download
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {analytics.top_downloaders.map((user) => (
                    <tr key={user.registration_id}>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {user.participant_name}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-700">
                        {user.certificate_number}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span
                          className={`font-medium ${
                            user.download_count >= user.download_limit
                              ? 'text-red-600'
                              : 'text-gray-900'
                          }`}
                        >
                          {user.download_count}/{user.download_limit}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(user.last_downloaded_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
```

##### **CertificateManagement.tsx**

Purpose: Admin component for managing individual certificates

```tsx
/**
 * CertificateManagement Component
 * Admin interface for managing certificate download limits
 */

import React, { useState } from 'react';
import {
  updateCertificateDownloadLimit,
  resetCertificateDownloadCount,
} from '../../lib/certificates-api';
import { toast } from 'react-hot-toast';

interface Props {
  registrationId: number;
  currentLimit: number;
  currentCount: number;
  participantName: string;
  onUpdate?: () => void;
}

export const CertificateManagement: React.FC<Props> = ({
  registrationId,
  currentLimit,
  currentCount,
  participantName,
  onUpdate,
}) => {
  const [newLimit, setNewLimit] = useState(currentLimit);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const handleUpdateLimit = async () => {
    if (newLimit === currentLimit) {
      toast.error('New limit must be different');
      return;
    }

    setIsUpdating(true);
    try {
      await updateCertificateDownloadLimit(registrationId, {
        new_limit: newLimit,
      });
      toast.success(`Download limit updated to ${newLimit}`);
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error('Failed to update limit');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleResetCount = async () => {
    if (!window.confirm(`Reset download count for ${participantName}?`)) {
      return;
    }

    setIsResetting(true);
    try {
      await resetCertificateDownloadCount(registrationId);
      toast.success('Download count reset to 0');
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error('Failed to reset count');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{participantName}</h3>
        <p className="text-sm text-gray-600">
          Current: {currentCount}/{currentLimit} downloads
        </p>
      </div>

      {/* Update Limit */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          New Download Limit
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            min="0"
            max="1000"
            value={newLimit}
            onChange={(e) => setNewLimit(parseInt(e.target.value) || 0)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleUpdateLimit}
            disabled={isUpdating || newLimit === currentLimit}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUpdating ? 'Updating...' : 'Update'}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">Set to 0 for unlimited downloads</p>
      </div>

      {/* Reset Count */}
      <div>
        <button
          onClick={handleResetCount}
          disabled={isResetting}
          className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isResetting ? 'Resetting...' : 'Reset Download Count'}
        </button>
      </div>
    </div>
  );
};
```

### 4. Integration Points

#### Update EventParticipantsWithProgress.tsx

Add certificate download button for completed registrations:

```tsx
// Add import
import { CertificateDownloadButton } from '../features/CertificateDownloadButton';

// In the render, after activity completion check:
{registration.activity_progress?.is_completed && (
  <div className="mt-4">
    <CertificateDownloadButton
      registration_id={registration.id}
      className="w-full"
    />
  </div>
)}
```

#### Update Navigation (Layout)

Add "My Certificates" link to user menu:

```tsx
<nav>
  <Link to="/my-races">My Races</Link>
  <Link to="/my-certificates">My Certificates</Link> {/* NEW */}
  <Link to="/profile">Profile</Link>
</nav>
```

#### Update Admin Dashboard

Add certificate analytics card:

```tsx
// In admin dashboard
import { CertificateAnalyticsDashboard } from '../components/features/CertificateAnalyticsDashboard';

<div className="admin-dashboard">
  {/* Existing cards */}

  {/* NEW: Certificate Analytics */}
  <div className="mt-8">
    <CertificateAnalyticsDashboard />
  </div>
</div>
```

---

## 📋 Implementation Checklist

### Phase 1: Core Functionality ✅ DONE
- [x] TypeScript types updated
- [x] API client created
- [x] Helper functions implemented

### Phase 2: User Components (TODO)
- [ ] Create `CertificateDownloadButton.tsx`
- [ ] Create `CertificateCard.tsx`
- [ ] Create `MyCertificatesPage.tsx`
- [ ] Add route for `/my-certificates`
- [ ] Integrate button into event completion UI
- [ ] Add navigation link

### Phase 3: Admin Components (TODO)
- [ ] Create `CertificateAnalyticsDashboard.tsx`
- [ ] Create `CertificateManagement.tsx`
- [ ] Integrate into admin dashboard
- [ ] Add admin navigation links

### Phase 4: Testing & Polish (TODO)
- [ ] Test user download flow
- [ ] Test download limits
- [ ] Test admin analytics
- [ ] Test admin limit updates
- [ ] Error handling
- [ ] Loading states
- [ ] Mobile responsiveness

---

## 🎨 UI/UX Specifications

### Colors
- Primary (Download): `bg-blue-600 hover:bg-blue-700`
- Success: `text-green-600`
- Warning: `text-orange-600`
- Error: `text-red-600`
- Disabled: `bg-gray-300 text-gray-500`

### Icons
- Certificate: 📜
- Download: Arrow down icon
- Loading: Spinner
- Success: Checkmark
- Error: X mark

### Animations
- Button hover: `transition-all duration-200`
- Loading spinner: `animate-spin`
- Card hover: `hover:shadow-lg transition-all`

---

## 🔗 API Endpoints Reference

### User Endpoints
- `GET /api/v1/certificates/registration/{id}` - Preview
- `GET /api/v1/certificates/registration/{id}/download` - Download
- `GET /api/v1/certificates/my-certificates` - List all

### Admin Endpoints
- `PATCH /api/v1/certificates/registration/{id}/download-limit` - Update limit
- `POST /api/v1/certificates/registration/{id}/reset-downloads` - Reset count
- `PATCH /api/v1/certificates/events/{id}/default-download-limit` - Event defaults
- `GET /api/v1/certificates/download-analytics` - Analytics

---

## 🚀 Quick Start for Frontend Developer

1. **Copy the type definitions and API client** (already done ✅)

2. **Create the three main user components:**
   - `CertificateDownloadButton.tsx` - Reusable download button
   - `CertificateCard.tsx` - Certificate display card
   - `MyCertificatesPage.tsx` - Full certificates page

3. **Integrate into existing pages:**
   - Add download button to event completion view
   - Add "My Certificates" navigation link
   - Add route for certificates page

4. **Create admin components** (if admin access required):
   - `CertificateAnalyticsDashboard.tsx` - Analytics overview
   - `CertificateManagement.tsx` - Manage individual certificates

5. **Test thoroughly:**
   - User can download certificate
   - Download count increments
   - Limit is enforced (HTTP 429)
   - Admin can reset/update limits

---

## 📱 Mobile Considerations

- Download button should be full-width on mobile
- Certificate cards should stack vertically
- Analytics should use responsive grid
- Table should scroll horizontally if needed

---

## ♿ Accessibility

- All buttons must have aria-labels
- Loading states must be announced
- Error messages must be clear
- Keyboard navigation support
- Focus indicators visible

---

## 🎯 Success Metrics

Once implemented, track:
- Certificate download rate (% of completed races)
- Average downloads per certificate
- Users hitting download limits
- Support tickets related to certificates
- Mobile vs desktop usage

---

**Implementation Status:** Ready to implement
**Estimated Time:** 4-6 hours for full implementation
**Backend Dependency:** ✅ Complete and deployed

All code examples are production-ready and follow React/TypeScript best practices!
