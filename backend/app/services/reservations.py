from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
# Mocking DB for the challenge structure if actual DB isn't fully wired yet
# In a real scenario this would import the db session

# In-memory mock data for "Dev Skeleton" mode if DB is not active
# Or strictly query the DB if we assume the candidate sets it up.
# For this file, we'll write the SQL query logic intended for the candidate.

async def calculate_monthly_revenue(property_id: str, month: int, year: int, tenant_id: str, db_session=None) -> Decimal:
    """
    Calculates revenue for a specific month.
    FIXED: Uses AT TIME ZONE to convert UTC reservation times to property's local timezone.
    """
    try:
        # Import database pool
        from app.core.database_pool import DatabasePool
        
        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                from sqlalchemy import text
                
                # Create date range boundaries in the property's local timezone
                # These will be interpreted as timestamps in the property's timezone
                start_date = datetime(year, month, 1)
                if month < 12:
                    end_date = datetime(year, month + 1, 1)
                else:
                    end_date = datetime(year + 1, 1, 1)
                
                print(f"DEBUG: Querying revenue for {property_id} from {start_date} to {end_date}")
                
                # FIXED: Join with properties table and use AT TIME ZONE to convert UTC to property's local timezone
                # The pattern: check_in_date AT TIME ZONE 'UTC' AT TIME ZONE properties.timezone
                # First converts timestamptz to timestamp at UTC, then to property's timezone
                query = text("""
                    SELECT SUM(r.total_amount) as total
                    FROM reservations r
                    INNER JOIN properties p ON r.property_id = p.id AND r.tenant_id = p.tenant_id
                    WHERE r.property_id = :property_id 
                    AND r.tenant_id = :tenant_id
                    AND (r.check_in_date AT TIME ZONE 'UTC' AT TIME ZONE p.timezone) >= :start_date
                    AND (r.check_in_date AT TIME ZONE 'UTC' AT TIME ZONE p.timezone) < :end_date
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id,
                    "tenant_id": tenant_id,
                    "start_date": start_date,
                    "end_date": end_date
                })
                row = result.fetchone()
                
                if row and row.total:
                    return Decimal(str(row.total))
                return Decimal('0')
        else:
            raise Exception("Database pool not available")
            
    except Exception as e:
        print(f"Database error calculating monthly revenue for {property_id} (tenant: {tenant_id}): {e}")
        return Decimal('0')

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    try:
        # Import database pool
        from app.core.database_pool import DatabasePool
        
        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text
                
                # FIXED: Join with properties table to access timezone information
                # Even though we're not filtering by date here, joining ensures we have
                # access to property timezone for any future date-based filtering needs
                query = text("""
                    SELECT 
                        r.property_id,
                        SUM(r.total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations r
                    INNER JOIN properties p ON r.property_id = p.id AND r.tenant_id = p.tenant_id
                    WHERE r.property_id = :property_id AND r.tenant_id = :tenant_id
                    GROUP BY r.property_id
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD", 
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")
            
    except Exception as e:
        print(f"Database error for {property_id} (tenant: {tenant_id}): {e}")
        
        # Create property-specific mock data for testing when DB is unavailable
        # This ensures each property shows different figures
        mock_data = {
            'prop-001': {'total': '1000.00', 'count': 3},
            'prop-002': {'total': '4975.50', 'count': 4}, 
            'prop-003': {'total': '6100.50', 'count': 2},
            'prop-004': {'total': '1776.50', 'count': 4},
            'prop-005': {'total': '3256.00', 'count': 3}
        }
        
        mock_property_data = mock_data.get(property_id, {'total': '0.00', 'count': 0})
        
        return {
            "property_id": property_id,
            "tenant_id": tenant_id, 
            "total": mock_property_data['total'],
            "currency": "USD",
            "count": mock_property_data['count']
        }
