import logging
from typing import List, Any, Optional
from ..interfaces import ISnapshotable

logger = logging.getLogger("agent.rollback")

class RollbackManager:
    """Manages environment snapshots for trajectory rollback functionality."""
    
    def __init__(self, env: ISnapshotable, max_snapshots: int = 10):
        self.env = env
        self.snapshots: List[Any] = []
        self.max_snapshots = max_snapshots

    async def checkpoint(self) -> int:
        """Saves a snapshot of the current environment state."""
        try:
            snapshot = await self.env.save_snapshot()
            self.snapshots.append(snapshot)
            
            # Enforce capacity
            if len(self.snapshots) > self.max_snapshots:
                self.snapshots.pop(0)
                
            ckpt_id = len(self.snapshots) - 1
            logger.info(f"Checkpoint created: {ckpt_id}")
            return ckpt_id
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return -1

    async def rollback(self, checkpoint_id: int) -> bool:
        """Restores the environment to the specified checkpoint."""
        if checkpoint_id < 0 or checkpoint_id >= len(self.snapshots):
            logger.warning(f"Invalid checkpoint ID: {checkpoint_id}")
            return False
            
        try:
            snapshot = self.snapshots[checkpoint_id]
            success = await self.env.restore_snapshot(snapshot)
            
            if success:
                # Discard future snapshots after rollback
                self.snapshots = self.snapshots[:checkpoint_id + 1]
                logger.info(f"Rolled back to checkpoint {checkpoint_id}")
            return success
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def rollback_n_steps(self, n: int) -> bool:
        """Rolls back n checkpoints."""
        target_id = len(self.snapshots) - 1 - n
        return await self.rollback(target_id)
        
    def clear(self):
        self.snapshots = []
