import logging
import threading
import time
import docker
import queue
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PooledContainer:
    def __init__(self, container, image_name: str):
        self.container = container
        self.image_name = image_name
        self.created_at = datetime.utcnow()
        self.last_used_at = None
        self.status = "warm" # warm, busy, dirty

class WarmPoolManager:
    def __init__(self, docker_client=None, min_size=2, max_size=5, ttl_seconds=300):
        self.docker = docker_client or docker.from_env()
        self.min_size = min_size
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Pools keyed by image name
        self.pools: Dict[str, queue.Queue] = {}
        self.active_containers: Dict[str, PooledContainer] = {} # container_id -> object
        self.lock = threading.Lock()
        
        self.running = False
        self.monitor_thread = None

    def start(self):
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("WarmPoolManager started")

    def stop(self):
        self.running = False
        # Cleanup all containers
        with self.lock:
            for cid, pooled in self.active_containers.items():
                try:
                    pooled.container.kill()
                    pooled.container.remove()
                except:
                    pass
            self.active_containers.clear()
            self.pools.clear()

    def get_container(self, image_name: str) -> Optional[PooledContainer]:
        """
        Get a warm container from the pool or create a new one if allowed.
        """
        # Ensure queue exists
        if image_name not in self.pools:
            self.pools[image_name] = queue.Queue()

        # Try to get from pool
        try:
            pooled = self.pools[image_name].get_nowait()
            # Validate health (basic check)
            pooled.container.reload()
            if pooled.container.status != 'running':
                logger.warning(f"Pooled container {pooled.container.short_id} is dead. Discarding.")
                self._remove_tracker(pooled.container.id)
                return self.get_container(image_name) # Retry
                
            pooled.status = "busy"
            pooled.last_used_at = datetime.utcnow()
            return pooled
            
        except queue.Empty:
            # Pool empty, create new one
            return self._create_container(image_name)

    def release_container(self, pooled: PooledContainer):
        """
        Return container to pool or destroy if dirty/old.
        For Turing Gym, tests often dirty the state, so default might be to destroy 
        unless we implement a 'reset' mechanism. 
        For Phase 3 MVP, we will destroy used containers and let the background filler replenish.
        """
        # In a real "warm pool" for production, we'd reset state.
        # For validation testing, "clean" is critical.
        # Strategy: 
        # 1. Kill the used container (it's dirty).
        # 2. Background monitor will see pool size < min_size and create fresh ones.
        try:
            pooled.container.kill()
            pooled.container.remove()
        except:
            pass
        self._remove_tracker(pooled.container.id)

    def _create_container(self, image_name: str) -> PooledContainer:
        """
        Internal: Create a new container and track it.
        """
        try:
            # Fallback logic same as Runner
            try:
                self.docker.images.get(image_name)
            except docker.errors.ImageNotFound:
                image_name = "python:3.11-slim"

            container = self.docker.containers.run(
                image_name,
                command="tail -f /dev/null", 
                detach=True
            )
            
            pooled = PooledContainer(container, image_name)
            with self.lock:
                self.active_containers[container.id] = pooled
            
            return pooled
        except Exception as e:
            logger.error(f"Failed to create container for {image_name}: {e}")
            raise e

    def _remove_tracker(self, container_id):
        with self.lock:
            if container_id in self.active_containers:
                del self.active_containers[container_id]

    def _monitor_loop(self):
        """
        Background task to maintain pool size.
        """
        while self.running:
            try:
                # 1. Replenish Pools
                target_images = ["python:3.11-slim"] 
                
                for img in target_images:
                    if img not in self.pools:
                        self.pools[img] = queue.Queue()
                        
                    current_size = self.pools[img].qsize()
                    
                    # Basic Scaling Logic: If we hit empty recently, bump min_size temporarily
                    # For MVP, just stick to min_size
                    
                    if current_size < self.min_size:
                        needed = self.min_size - current_size
                        logger.info(f"Replenishing pool for {img}: need {needed}")
                        for _ in range(needed):
                            try:
                                pooled = self._create_container(img)
                                pooled.status = "warm"
                                self.pools[img].put(pooled)
                            except Exception as e:
                                logger.error(f"Pool replenishment failed: {e}")
                                
                # 2. Health Check & Cleanup
                # Check active containers for TTL
                now = datetime.utcnow()
                with self.lock:
                    to_remove = []
                    for cid, pooled in self.active_containers.items():
                        # If warm but too old, kill it (refresh pool)
                        if pooled.status == "warm" and (now - pooled.created_at).total_seconds() > self.ttl_seconds:
                            logger.info(f"Container {cid} expired TTL. Rotating.")
                            try:
                                pooled.container.kill()
                                pooled.container.remove()
                            except:
                                pass
                            to_remove.append(cid)
                    
                    for cid in to_remove:
                        del self.active_containers[cid]
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                
            time.sleep(5) # Check every 5 seconds

    def get_stats(self) -> Dict[str, Any]:
        """
        Return pool statistics for metrics.
        """
        stats = {
            "active_containers": len(self.active_containers),
            "pools": {}
        }
        for img, q in self.pools.items():
            stats["pools"][img] = q.qsize()
        return stats
