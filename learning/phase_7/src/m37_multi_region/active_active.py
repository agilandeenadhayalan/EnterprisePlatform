"""
Active-Active Replication — multi-region clusters with conflict detection.

WHY THIS MATTERS:
Global platforms must serve users from the nearest region with low latency.
Active-active replication lets every region accept writes, but this creates
the fundamental challenge of distributed systems: concurrent writes to the
same data in different regions. You need replication topologies to propagate
changes efficiently and conflict detection to identify when two regions
wrote to the same key without seeing each other's update.

Key concepts:
  - Replication modes: active-active (all write), active-passive (one writes),
    multi-primary (multiple leaders with conflict resolution).
  - Replication topologies: ring, star, mesh — each trades propagation delay
    for bandwidth and fault tolerance differently.
  - Version vectors: track causality across regions. If two version vectors
    are incomparable, the writes are concurrent and need conflict resolution.
  - Consistency levels: one (fast, stale), quorum (balanced), all (slow, fresh).
"""

import time
import copy
from enum import Enum
from dataclasses import dataclass, field


class ReplicationMode(Enum):
    """How regions coordinate writes."""
    active_active = "active_active"
    active_passive = "active_passive"
    multi_primary = "multi_primary"


@dataclass
class RegionReplica:
    """State of a single region in the cluster.

    Attributes:
        region_code: unique region identifier (e.g., "us-east-1")
        role: "leader" or "follower"
        data_version: monotonic version counter for this region
        lag_ms: replication lag in milliseconds
        is_healthy: whether this region is accepting traffic
    """
    region_code: str
    role: str = "leader"
    data_version: int = 0
    lag_ms: float = 0.0
    is_healthy: bool = True


class ReplicationTopology:
    """Manages replication topology: ring, star, or mesh.

    Ring: each node replicates to the next in a circle.
    Star: one hub replicates to all spokes.
    Mesh: every node replicates to every other node.
    """

    def __init__(self, topology_type: str = "mesh"):
        self.topology_type = topology_type
        self._nodes: list[str] = []

    def add_node(self, node_id: str) -> None:
        """Add a node to the topology."""
        if node_id not in self._nodes:
            self._nodes.append(node_id)

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the topology."""
        if node_id in self._nodes:
            self._nodes.remove(node_id)

    def get_replication_targets(self, node_id: str) -> list[str]:
        """Return the list of nodes this node should replicate to."""
        if node_id not in self._nodes:
            return []

        idx = self._nodes.index(node_id)
        others = [n for n in self._nodes if n != node_id]

        if self.topology_type == "ring":
            if len(self._nodes) < 2:
                return []
            next_idx = (idx + 1) % len(self._nodes)
            return [self._nodes[next_idx]]
        elif self.topology_type == "star":
            # First node is the hub
            if idx == 0:
                return others
            else:
                return [self._nodes[0]]
        else:  # mesh
            return others

    @property
    def nodes(self) -> list[str]:
        return list(self._nodes)


class ActiveActiveCluster:
    """Multi-region active-active cluster with replication log.

    Every region can accept writes. The replication log captures all writes
    so they can be propagated to other regions. Reads can use different
    consistency levels depending on the freshness requirement.
    """

    def __init__(self, mode: ReplicationMode = ReplicationMode.active_active):
        self.mode = mode
        self.replicas: dict[str, RegionReplica] = {}
        self.replication_log: list[dict] = []
        self._data: dict[str, dict[str, object]] = {}  # region -> {key: value}

    def add_region(self, region_code: str, role: str = "leader") -> None:
        """Register a region in the cluster."""
        self.replicas[region_code] = RegionReplica(
            region_code=region_code, role=role
        )
        self._data[region_code] = {}

    def write(self, key: str, value: object, region: str) -> None:
        """Write a key-value pair to a specific region.

        Records the write in the replication log for later propagation.
        """
        if region not in self.replicas:
            raise ValueError(f"Unknown region: {region}")

        replica = self.replicas[region]
        replica.data_version += 1
        self._data[region][key] = value

        self.replication_log.append({
            "key": key,
            "value": value,
            "region": region,
            "version": replica.data_version,
            "timestamp": time.time(),
            "replicated": False,
        })

    def read(self, key: str, consistency: str = "one") -> object:
        """Read a key with the given consistency level.

        Consistency levels:
          - "one": read from any region that has the key (fast)
          - "quorum": read from majority of regions, return latest version
          - "all": read from all regions, return latest version
        """
        if consistency == "one":
            for region_data in self._data.values():
                if key in region_data:
                    return region_data[key]
            return None

        # For quorum/all, collect all values and return the latest
        values = []
        for region_code, region_data in self._data.items():
            if key in region_data:
                values.append((
                    self.replicas[region_code].data_version,
                    region_data[key],
                ))

        required = len(self.replicas) // 2 + 1 if consistency == "quorum" else len(self.replicas)

        if len(values) >= required:
            # Return value with highest version
            values.sort(key=lambda x: x[0], reverse=True)
            return values[0][1]
        elif values:
            return values[0][1]
        return None

    def replicate(self) -> int:
        """Propagate unreplicated writes to all other regions.

        Returns the number of entries replicated.
        """
        count = 0
        for entry in self.replication_log:
            if entry["replicated"]:
                continue
            source = entry["region"]
            for region_code in self._data:
                if region_code != source:
                    self._data[region_code][entry["key"]] = entry["value"]
                    self.replicas[region_code].lag_ms = 0.0
                    count += 1
            entry["replicated"] = True
        return count

    def get_lag(self, region: str) -> float:
        """Return replication lag for a region in milliseconds."""
        if region not in self.replicas:
            raise ValueError(f"Unknown region: {region}")

        # Count unreplicated entries targeting this region
        unreplicated = sum(
            1 for e in self.replication_log
            if not e["replicated"] and e["region"] != region
        )
        # Simulate lag proportional to unreplicated entries
        return float(unreplicated * 50)  # 50ms per pending entry


class ConflictDetector:
    """Detect concurrent writes using version vectors.

    A version vector is a dict mapping region -> version_number. Two writes
    are concurrent if neither version vector dominates the other — i.e.,
    each has at least one component strictly greater than the other.
    """

    def check(
        self,
        version_a: dict[str, int],
        version_b: dict[str, int],
    ) -> str:
        """Compare two version vectors.

        Returns:
            "a_newer" if a happened after b,
            "b_newer" if b happened after a,
            "concurrent" if neither dominates (conflict!),
            "equal" if they are identical.
        """
        all_keys = set(version_a.keys()) | set(version_b.keys())

        a_greater = False
        b_greater = False

        for key in all_keys:
            va = version_a.get(key, 0)
            vb = version_b.get(key, 0)
            if va > vb:
                a_greater = True
            elif vb > va:
                b_greater = True

        if a_greater and b_greater:
            return "concurrent"
        elif a_greater:
            return "a_newer"
        elif b_greater:
            return "b_newer"
        else:
            return "equal"
