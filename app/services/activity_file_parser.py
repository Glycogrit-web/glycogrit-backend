"""
Activity File Parser Service
Parses GPX, TCX, and FIT files to extract activity data
Processes files in memory without saving them
"""

import logging
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import gpxpy
import gpxpy.gpx

logger = logging.getLogger(__name__)


class ActivityFileParser:
    """Parse activity files (GPX, TCX, FIT) and extract data"""

    @staticmethod
    def parse_gpx(file_content: bytes) -> dict:
        """
        Parse GPX file and extract activity data

        Args:
            file_content: Raw GPX file bytes

        Returns:
            Dict with distance_km, duration_minutes, activity_date, activity_type
        """
        try:
            gpx = gpxpy.parse(file_content.decode('utf-8'))

            # Extract data
            total_distance_m = 0
            total_duration_sec = 0
            start_time = None
            end_time = None

            for track in gpx.tracks:
                for segment in track.segments:
                    # Get segment distance
                    segment_distance = segment.length_2d()  # 2D distance in meters
                    total_distance_m += segment_distance

                    # Get time information
                    if segment.points:
                        if not start_time and segment.points[0].time:
                            start_time = segment.points[0].time
                        if segment.points[-1].time:
                            end_time = segment.points[-1].time

            # Calculate duration
            if start_time and end_time:
                duration = end_time - start_time
                total_duration_sec = duration.total_seconds()

            # Use start time or current time
            activity_date = start_time if start_time else datetime.now(timezone.utc)

            # Ensure timezone awareness
            if activity_date.tzinfo is None:
                activity_date = activity_date.replace(tzinfo=timezone.utc)

            return {
                "distance_km": round(total_distance_m / 1000, 2),
                "duration_minutes": int(total_duration_sec // 60),
                "activity_date": activity_date,
                "activity_type": "Run",  # Default to Run
                "source": "manual_upload",
                "file_format": "gpx"
            }

        except Exception as e:
            logger.error(f"Error parsing GPX file: {e}")
            raise ValueError(f"Invalid GPX file: {str(e)}")

    @staticmethod
    def parse_tcx(file_content: bytes) -> dict:
        """
        Parse TCX (Training Center XML) file and extract activity data

        Args:
            file_content: Raw TCX file bytes

        Returns:
            Dict with distance_km, duration_minutes, activity_date, activity_type
        """
        try:
            root = ET.fromstring(file_content.decode('utf-8'))

            # TCX namespace
            ns = {
                'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
                'ext': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
            }

            # Find activity
            activity = root.find('.//tcx:Activity', ns)
            if activity is None:
                raise ValueError("No activity found in TCX file")

            # Get activity type
            activity_type = activity.get('Sport', 'Run')

            # Extract data from laps
            total_distance_m = 0
            total_duration_sec = 0
            start_time = None

            laps = activity.findall('.//tcx:Lap', ns)
            for lap in laps:
                # Get start time from first lap
                if not start_time and 'StartTime' in lap.attrib:
                    start_time_str = lap.attrib['StartTime']
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))

                # Get distance
                distance_elem = lap.find('.//tcx:DistanceMeters', ns)
                if distance_elem is not None and distance_elem.text:
                    total_distance_m += float(distance_elem.text)

                # Get duration
                duration_elem = lap.find('.//tcx:TotalTimeSeconds', ns)
                if duration_elem is not None and duration_elem.text:
                    total_duration_sec += float(duration_elem.text)

            # Use start time or current time
            activity_date = start_time if start_time else datetime.now(timezone.utc)

            return {
                "distance_km": round(total_distance_m / 1000, 2),
                "duration_minutes": int(total_duration_sec // 60),
                "activity_date": activity_date,
                "activity_type": activity_type,
                "source": "manual_upload",
                "file_format": "tcx"
            }

        except Exception as e:
            logger.error(f"Error parsing TCX file: {e}")
            raise ValueError(f"Invalid TCX file: {str(e)}")

    @staticmethod
    def parse_fit(file_content: bytes) -> dict:
        """
        Parse FIT file and extract activity data

        Args:
            file_content: Raw FIT file bytes

        Returns:
            Dict with distance_km, duration_minutes, activity_date, activity_type
        """
        try:
            from io import BytesIO

            from fitparse import FitFile

            # Parse FIT file from bytes
            fit_file = FitFile(BytesIO(file_content))

            total_distance_m = 0
            total_duration_sec = 0
            start_time = None
            activity_type = "Run"

            # Parse records
            for record in fit_file.get_messages():
                # Get session summary (contains totals)
                if record.name == 'session':
                    for field in record.fields:
                        if field.name == 'total_distance':
                            total_distance_m = field.value
                        elif field.name == 'total_timer_time':
                            total_duration_sec = field.value
                        elif field.name == 'start_time':
                            start_time = field.value
                        elif field.name == 'sport':
                            activity_type = field.value or "Run"

            # Use start time or current time
            activity_date = start_time if start_time else datetime.now(timezone.utc)

            # Ensure timezone awareness
            if activity_date.tzinfo is None:
                activity_date = activity_date.replace(tzinfo=timezone.utc)

            return {
                "distance_km": round(total_distance_m / 1000, 2),
                "duration_minutes": int(total_duration_sec // 60),
                "activity_date": activity_date,
                "activity_type": str(activity_type).capitalize(),
                "source": "manual_upload",
                "file_format": "fit"
            }

        except ImportError:
            raise ValueError("FIT file parsing library not installed. Please install fitparse.")
        except Exception as e:
            logger.error(f"Error parsing FIT file: {e}")
            raise ValueError(f"Invalid FIT file: {str(e)}")

    @classmethod
    def parse_activity_file(cls, file_content: bytes, filename: str) -> dict:
        """
        Auto-detect file type and parse activity data

        Args:
            file_content: Raw file bytes
            filename: Original filename

        Returns:
            Dict with parsed activity data
        """
        filename_lower = filename.lower()

        if filename_lower.endswith('.gpx'):
            return cls.parse_gpx(file_content)
        elif filename_lower.endswith('.tcx'):
            return cls.parse_tcx(file_content)
        elif filename_lower.endswith('.fit'):
            return cls.parse_fit(file_content)
        else:
            raise ValueError(
                f"Unsupported file format. Please upload .gpx, .tcx, or .fit files. "
                f"Got: {filename}"
            )
