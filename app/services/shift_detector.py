from datetime import datetime, time, timedelta
from typing import Tuple, Optional
from app.config import get_settings
from app.models.attendance import ShiftType

settings = get_settings()


class ShiftDetector:
    """
    Detects shift based on punch timestamp
    Handles edge cases like night shifts crossing midnight
    """
    
    def __init__(self):
        self.shifts = settings.shift_timings
    
    def detect_shift(self, punch_time: datetime) -> ShiftType:
        """
        Detect which shift a punch belongs to based on timestamp
        
        Args:
            punch_time: The timestamp of the punch
            
        Returns:
            ShiftType enum value
        """
        punch_hour_minute = punch_time.time()
        
        # Check Shift A (07:00 - 15:00)
        if self._is_in_shift(punch_hour_minute, "A"):
            return ShiftType.A
        
        # Check Shift B (15:00 - 23:00)
        if self._is_in_shift(punch_hour_minute, "B"):
            return ShiftType.B
        
        # Check Shift G (09:00 - 17:00) - overlaps with A
        # Prioritize based on proximity to shift start
        if self._is_in_shift(punch_hour_minute, "G"):
            # If time is closer to 09:00 than 07:00, it's likely General shift
            if punch_hour_minute >= time(9, 0) and punch_hour_minute < time(15, 0):
                return ShiftType.G
            return ShiftType.A
        
        # Check Shift C (23:00 - 07:00) - night shift crossing midnight
        if self._is_in_shift(punch_hour_minute, "C"):
            return ShiftType.C
        
        # Default to nearest shift if unclear
        return self._get_nearest_shift(punch_hour_minute)
    
    def _is_in_shift(self, punch_time: time, shift_code: str) -> bool:
        """Check if punch time falls within a shift"""
        shift = self.shifts[shift_code]
        start = shift["start"]
        end = shift["end"]
        
        # Handle night shift that crosses midnight
        if start > end:  # e.g., 23:00 to 07:00
            return punch_time >= start or punch_time < end
        else:
            return start <= punch_time < end
    
    def _get_nearest_shift(self, punch_time: time) -> ShiftType:
        """Get nearest shift when time is ambiguous"""
        # Convert time to minutes since midnight for comparison
        punch_minutes = punch_time.hour * 60 + punch_time.minute
        
        min_distance = float('inf')
        nearest_shift = ShiftType.A
        
        for shift_code, shift_data in self.shifts.items():
            start_minutes = shift_data["start"].hour * 60 + shift_data["start"].minute
            distance = abs(punch_minutes - start_minutes)
            
            if distance < min_distance:
                min_distance = distance
                nearest_shift = ShiftType[shift_code]
        
        return nearest_shift
    
    def calculate_late_minutes(
        self, 
        punch_time: datetime, 
        shift: ShiftType
    ) -> Tuple[bool, int]:
        """
        Calculate if employee is late and by how many minutes
        
        Args:
            punch_time: First IN punch of the day
            shift: Detected shift
            
        Returns:
            Tuple of (is_late: bool, minutes_late: int)
        """
        shift_data = self.shifts[shift.value]
        expected_start = shift_data["start"]
        grace_period = settings.LATE_GRACE_MINUTES
        
        # Convert to comparable format
        punch_time_only = punch_time.time()
        
        # Handle night shift
        if shift == ShiftType.C and punch_time_only < time(12, 0):
            # If punch is before noon and shift starts at 23:00, employee is very late
            expected_datetime = datetime.combine(
                punch_time.date() - timedelta(days=1), 
                expected_start
            )
        else:
            expected_datetime = datetime.combine(punch_time.date(), expected_start)
        
        # Calculate difference
        late_by = (punch_time - expected_datetime).total_seconds() / 60
        
        is_late = late_by > grace_period
        minutes_late = max(0, int(late_by))
        
        return is_late, minutes_late
    
    def calculate_early_leave_minutes(
        self, 
        punch_time: datetime, 
        shift: ShiftType
    ) -> Tuple[bool, int]:
        """
        Calculate if employee left early and by how many minutes
        
        Args:
            punch_time: Last OUT punch of the day
            shift: Detected shift
            
        Returns:
            Tuple of (is_early_leave: bool, minutes_early: int)
        """
        shift_data = self.shifts[shift.value]
        expected_end = shift_data["end"]
        grace_period = settings.EARLY_LEAVE_GRACE_MINUTES
        
        punch_time_only = punch_time.time()
        
        # Handle night shift
        if shift == ShiftType.C and punch_time_only < expected_end:
            # Night shift ends next day
            expected_datetime = datetime.combine(
                punch_time.date(), 
                expected_end
            )
        else:
            expected_datetime = datetime.combine(punch_time.date(), expected_end)
        
        # Calculate difference
        early_by = (expected_datetime - punch_time).total_seconds() / 60
        
        is_early = early_by > grace_period
        minutes_early = max(0, int(early_by))
        
        return is_early, minutes_early
    
    def calculate_work_duration(
        self, 
        first_in: datetime, 
        last_out: datetime
    ) -> float:
        """
        Calculate work duration in hours
        
        Args:
            first_in: First punch IN time
            last_out: Last punch OUT time
            
        Returns:
            Work duration in hours (rounded to 2 decimals)
        """
        duration = (last_out - first_in).total_seconds() / 3600
        return round(duration, 2)
    
    def get_expected_shift_hours(self, shift: ShiftType) -> float:
        """Get expected work hours for a shift"""
        shift_data = self.shifts[shift.value]
        start = shift_data["start"]
        end = shift_data["end"]
        
        # Convert to minutes
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        
        # Handle overnight shifts
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        duration_minutes = end_minutes - start_minutes
        return round(duration_minutes / 60, 2)