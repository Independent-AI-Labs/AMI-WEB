"""Migration script to transition from old BrowserPool to new worker pool system."""

import asyncio
import sys
from pathlib import Path

from loguru import logger

# Add browser to path
browser_path = Path(__file__).parent.parent.parent.parent
if str(browser_path) not in sys.path:
    sys.path.insert(0, str(browser_path))

from backend.core.management.manager import ChromeManager
from backend.core.management.manager_v2 import ChromeManagerV2


async def migrate_chrome_manager(old_manager: ChromeManager) -> ChromeManagerV2:
    """Migrate from old ChromeManager to new ChromeManagerV2.
    
    Args:
        old_manager: The existing ChromeManager instance
        
    Returns:
        A new ChromeManagerV2 instance with migrated settings
    """
    logger.info("Starting migration from ChromeManager to ChromeManagerV2")
    
    # Create new manager with same config
    new_manager = ChromeManagerV2(config_file=None)
    new_manager.config = old_manager.config
    new_manager.properties_manager = old_manager.properties_manager
    new_manager.profile_manager = old_manager.profile_manager
    new_manager.session_manager = old_manager.session_manager
    
    # Initialize the new manager
    await new_manager.initialize()
    
    # Migrate pool settings
    logger.info("Migrated pool settings:")
    logger.info(f"  - Min instances: {old_manager.pool.min_instances}")
    logger.info(f"  - Max instances: {old_manager.pool.max_instances}")
    logger.info(f"  - Warm instances: {old_manager.pool.warm_instances}")
    logger.info(f"  - Instance TTL: {old_manager.pool.instance_ttl}")
    logger.info(f"  - Health check interval: {old_manager.pool.health_check_interval}")
    
    # Note: We don't migrate active instances as they should be properly closed
    # and recreated to avoid state issues
    logger.warning("Active browser instances will need to be recreated")
    
    logger.info("Migration complete!")
    return new_manager


def update_imports_in_file(file_path: Path) -> bool:
    """Update imports in a Python file to use manager_v2.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        True if file was modified, False otherwise
    """
    if not file_path.exists():
        return False
        
    content = file_path.read_text()
    original_content = content
    
    # Replace imports
    replacements = [
        (
            "from backend.core.management.manager import ChromeManager",
            "from backend.core.management.manager_v2 import ChromeManagerV2 as ChromeManager"
        ),
        (
            "from .manager import ChromeManager",
            "from .manager_v2 import ChromeManagerV2 as ChromeManager"
        ),
        (
            "from ..management.manager import ChromeManager",
            "from ..management.manager_v2 import ChromeManagerV2 as ChromeManager"
        ),
        (
            "from ...core.management.manager import ChromeManager",
            "from ...core.management.manager_v2 import ChromeManagerV2 as ChromeManager"
        ),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    if content != original_content:
        file_path.write_text(content)
        logger.info(f"Updated imports in {file_path}")
        return True
        
    return False


def migrate_codebase(browser_dir: Path) -> None:
    """Migrate entire codebase to use the new manager.
    
    Args:
        browser_dir: Path to the browser module directory
    """
    logger.info("Migrating codebase to use ChromeManagerV2")
    
    # Find all Python files that might import ChromeManager
    python_files = list(browser_dir.rglob("*.py"))
    
    modified_count = 0
    for file_path in python_files:
        # Skip migration files and the old manager itself
        if file_path.name in ["migrate_to_v2.py", "manager.py", "pool.py"]:
            continue
            
        if update_imports_in_file(file_path):
            modified_count += 1
    
    logger.info(f"Modified {modified_count} files")


async def test_new_pool() -> None:
    """Test the new pool system."""
    logger.info("Testing new ChromeManagerV2...")
    
    manager = ChromeManagerV2()
    await manager.initialize()
    
    try:
        # Test getting an instance from pool
        logger.info("Getting instance from pool...")
        instance1 = await manager.get_or_create_instance(headless=True)
        logger.info(f"Got instance: {instance1.id}")
        
        # Test pool stats
        stats = await manager.get_pool_stats()
        logger.info(f"Pool stats: {stats}")
        
        # Test returning to pool
        logger.info("Returning instance to pool...")
        await manager.return_to_pool(instance1.id)
        
        # Test getting another instance (should reuse)
        logger.info("Getting another instance (should reuse from pool)...")
        instance2 = await manager.get_or_create_instance(headless=True)
        logger.info(f"Got instance: {instance2.id}")
        
        # Test standalone instance
        logger.info("Creating standalone instance...")
        instance3 = await manager.get_or_create_instance(headless=True, use_pool=False)
        logger.info(f"Got standalone instance: {instance3.id}")
        
        # List all instances
        instances = await manager.list_instances()
        logger.info(f"Total instances: {len(instances)}")
        for inst in instances:
            logger.info(f"  - {inst.id}: {inst.status}")
        
        # Final stats
        final_stats = await manager.get_pool_stats()
        logger.info(f"Final pool stats: {final_stats}")
        
    finally:
        await manager.shutdown()
        logger.info("Test complete!")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_new_pool())