"""
Supabase service for database operations.

This service provides a centralized interface for interacting with Supabase,
including tables for farms, consultants, and plots metadata.
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
import logging

if TYPE_CHECKING:
    from supabase import Client

try:
    from supabase import create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    create_client = None  # type: ignore
    SUPABASE_AVAILABLE = False

from core.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for managing Supabase database operations."""

    def __init__(self):
        """Initialize Supabase client if configured."""
        self.client: Optional["Client"] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Supabase client with credentials from settings."""
        if not settings.supabase_url or not settings.supabase_key:
            logger.warning(
                "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables."
            )
            return

        if not SUPABASE_AVAILABLE:
            logger.error(
                "Supabase library not installed. Install with: uv add supabase"
            )
            return

        try:
            self.client = create_client(settings.supabase_url, settings.supabase_key)  # type: ignore
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if Supabase is properly configured and available."""
        return self.client is not None

    # ==================== FARMS TABLE ====================

    async def get_farm_by_name(self, farm_name: str) -> Optional[Dict[str, Any]]:
        """
        Get farm details by name.

        Args:
            farm_name: Name of the farm to search for

        Returns:
            Farm data if found, None otherwise
        """
        if not self.is_available():
            logger.warning("Supabase not available for farm lookup")
            return None

        try:
            response = (
                self.client.table("farms")
                .select("*")
                .ilike("name", farm_name)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(f"Found farm: {farm_name}")
                return response.data[0]

            logger.info(f"Farm not found: {farm_name}")
            return None

        except Exception as e:
            logger.error(f"Error fetching farm '{farm_name}': {e}")
            return None

    async def create_farm(
        self,
        name: str,
        owner: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        total_area: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new farm entry.

        Args:
            name: Farm name
            owner: Owner name
            city: City location
            state: State location
            total_area: Total farm area in hectares

        Returns:
            Created farm data or None on error
        """
        if not self.is_available():
            return None

        try:
            farm_data = {
                "name": name,
                "owner": owner,
                "city": city,
                "state": state,
                "total_area": total_area,
                "created_at": datetime.now().isoformat(),
            }

            response = self.client.table("farms").insert(farm_data).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"Farm created: {name}")
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error creating farm '{name}': {e}")
            return None

    async def list_farms(self) -> List[Dict[str, Any]]:
        """Get all farms."""
        if not self.is_available():
            return []

        try:
            response = self.client.table("farms").select("*").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing farms: {e}")
            return []

    # ==================== CONSULTANTS TABLE ====================

    async def get_consultant_by_name(
        self, consultant_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get consultant details by name.

        Args:
            consultant_name: Name of the consultant

        Returns:
            Consultant data if found, None otherwise
        """
        if not self.is_available():
            return None

        try:
            response = (
                self.client.table("consultants")
                .select("*")
                .ilike("name", consultant_name)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(f"Found consultant: {consultant_name}")
                return response.data[0]

            logger.info(f"Consultant not found: {consultant_name}")
            return None

        except Exception as e:
            logger.error(f"Error fetching consultant '{consultant_name}': {e}")
            return None

    async def create_consultant(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        specialization: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new consultant entry."""
        if not self.is_available():
            return None

        try:
            consultant_data = {
                "name": name,
                "email": email,
                "phone": phone,
                "specialization": specialization,
                "created_at": datetime.now().isoformat(),
            }

            response = (
                self.client.table("consultants").insert(consultant_data).execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(f"Consultant created: {name}")
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error creating consultant '{name}': {e}")
            return None

    # ==================== PLOTS TABLE ====================

    async def get_plot_by_name(
        self, plot_name: str, farm_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get plot details by name, optionally filtered by farm.

        Args:
            plot_name: Name of the plot
            farm_id: Optional farm ID to narrow search

        Returns:
            Plot data if found, None otherwise
        """
        if not self.is_available():
            return None

        try:
            query = self.client.table("plots").select("*").ilike("name", plot_name)

            if farm_id:
                query = query.eq("farm_id", farm_id)

            response = query.limit(1).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"Found plot: {plot_name}")
                return response.data[0]

            logger.info(f"Plot not found: {plot_name}")
            return None

        except Exception as e:
            logger.error(f"Error fetching plot '{plot_name}': {e}")
            return None

    async def create_plot(
        self,
        name: str,
        farm_id: int,
        area: Optional[float] = None,
        variety: Optional[str] = None,
        planting_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new plot entry."""
        if not self.is_available():
            return None

        try:
            plot_data = {
                "name": name,
                "farm_id": farm_id,
                "area": area,
                "variety": variety,
                "planting_date": planting_date,
                "created_at": datetime.now().isoformat(),
            }

            response = self.client.table("plots").insert(plot_data).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"Plot created: {name}")
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error creating plot '{name}': {e}")
            return None

    # ==================== HELPER METHODS ====================

    async def enrich_report_metadata(
        self, farm_name: Optional[str] = None, consultant_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich report with metadata from Supabase.

        Args:
            farm_name: Name of the farm
            consultant_name: Name of the consultant

        Returns:
            Dictionary with enriched metadata
        """
        metadata = {}

        if farm_name:
            farm = await self.get_farm_by_name(farm_name)
            if farm:
                metadata["farm_name"] = farm.get("name")
                metadata["owner_name"] = farm.get("owner")
                metadata["farm_city"] = farm.get("city")
                metadata["farm_state"] = farm.get("state")
                metadata["farm_total_area"] = farm.get("total_area")

        if consultant_name:
            consultant = await self.get_consultant_by_name(consultant_name)
            if consultant:
                metadata["consultant_name"] = consultant.get("name")
                metadata["consultant_email"] = consultant.get("email")
                metadata["consultant_phone"] = consultant.get("phone")

        return metadata


# Global instance
supabase_service = SupabaseService()
