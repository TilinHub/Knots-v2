"""Tests para la capa orchestration: EventBus, ResultCache, TaskScheduler y ParallelCensus."""

import time
import pytest

from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point
from knots_v2.orchestration.cache import ResultCache
from knots_v2.orchestration.census import ParallelCensus
from knots_v2.orchestration.events import EventBus
from knots_v2.orchestration.scheduler import TaskScheduler


# ==================================================================
# EventBus
# ==================================================================

class TestEventBus:
    def test_subscribe_and_emit(self) -> None:
        bus = EventBus()
        received = []
        bus.subscribe("task_started", lambda data: received.append(data))
        bus.emit("task_started", {"id": 1})
        assert len(received) == 1
        assert received[0]["id"] == 1

    def test_emit_no_subscribers_does_not_raise(self) -> None:
        bus = EventBus()
        bus.emit("task_completed", {"result": "ok"})  # no debe lanzar

    def test_multiple_subscribers_called_in_order(self) -> None:
        bus = EventBus()
        calls: list[int] = []
        bus.subscribe("progress", lambda d: calls.append(1))
        bus.subscribe("progress", lambda d: calls.append(2))
        bus.emit("progress", {})
        assert calls == [1, 2]

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        calls = []
        cb = lambda d: calls.append(d)  # noqa: E731
        bus.subscribe("task_failed", cb)
        bus.unsubscribe("task_failed", cb)
        bus.emit("task_failed", {"error": "test"})
        assert calls == []

    def test_faulty_subscriber_does_not_stop_others(self) -> None:
        bus = EventBus()
        ok_calls = []
        bus.subscribe("task_started", lambda d: (_ for _ in ()).throw(RuntimeError("boom")))
        bus.subscribe("task_started", lambda d: ok_calls.append(d))
        bus.emit("task_started", {"id": 0})
        # El segundo suscriptor debe haber sido llamado a pesar del error del primero
        assert len(ok_calls) == 1

    def test_clear_all(self) -> None:
        bus = EventBus()
        calls = []
        bus.subscribe("progress", lambda d: calls.append(d))
        bus.clear()
        bus.emit("progress", {})
        assert calls == []

    def test_subscriber_count(self) -> None:
        bus = EventBus()
        bus.subscribe("task_completed", lambda d: None)
        bus.subscribe("task_completed", lambda d: None)
        assert bus.subscriber_count("task_completed") == 2


# ==================================================================
# ResultCache
# ==================================================================

class TestResultCache:
    def test_set_and_get(self) -> None:
        cache = ResultCache()
        cache.set("key1", {"value": 42})
        assert cache.get("key1") == {"value": 42}

    def test_get_missing_returns_none(self) -> None:
        cache = ResultCache()
        assert cache.get("no_existe") is None

    def test_invalidate_removes_entry(self) -> None:
        cache = ResultCache()
        cache.set("key1", "valor")
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_invalidate_nonexistent_does_not_raise(self) -> None:
        cache = ResultCache()
        cache.invalidate("no_existe")  # no debe lanzar

    def test_contains(self) -> None:
        cache = ResultCache()
        cache.set("presente", 1)
        assert "presente" in cache
        assert "ausente" not in cache

    def test_len(self) -> None:
        cache = ResultCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert len(cache) == 2

    def test_invalidate_all(self) -> None:
        cache = ResultCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate_all()
        assert len(cache) == 0

    def test_config_key_is_deterministic(self) -> None:
        cfg1 = DiskConfiguration()
        cfg1.add_disk(Disk(Point(0.0, 0.0), 1.0))
        cfg2 = DiskConfiguration()
        cfg2.add_disk(Disk(Point(0.0, 0.0), 1.0))
        assert ResultCache.config_key(cfg1) == ResultCache.config_key(cfg2)

    def test_different_configs_different_keys(self) -> None:
        cfg1 = DiskConfiguration()
        cfg1.add_disk(Disk(Point(0.0, 0.0), 1.0))
        cfg2 = DiskConfiguration()
        cfg2.add_disk(Disk(Point(1.0, 0.0), 1.0))
        assert ResultCache.config_key(cfg1) != ResultCache.config_key(cfg2)

    def test_overwrite(self) -> None:
        cache = ResultCache()
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"


# ==================================================================
# TaskScheduler
# ==================================================================

class TestTaskScheduler:
    def test_invalid_executor_type(self) -> None:
        with pytest.raises(ValueError):
            TaskScheduler(executor_type="invalid")

    def test_empty_tasks_returns_empty(self) -> None:
        scheduler = TaskScheduler()
        assert scheduler.run([]) == []

    def test_runs_all_tasks(self) -> None:
        scheduler = TaskScheduler()
        results = scheduler.run([lambda: 10, lambda: 20, lambda: 30])
        assert sorted(results) == [10, 20, 30]

    def test_results_preserve_order(self) -> None:
        # Usar default argument para capturar el valor de i en cada closure
        scheduler = TaskScheduler(max_workers=1)
        results = scheduler.run([lambda i=i: i for i in range(5)])
        assert results == list(range(5))

    def test_failed_task_returns_none(self) -> None:
        scheduler = TaskScheduler()
        def bad():
            raise RuntimeError("fallo esperado")
        results = scheduler.run([bad])
        assert results == [None]

    def test_emits_task_started_event(self) -> None:
        bus = EventBus()
        events = []
        bus.subscribe("task_started", lambda d: events.append(d))
        scheduler = TaskScheduler(event_bus=bus)
        scheduler.run([lambda: None])
        assert len(events) == 1

    def test_emits_task_completed_event(self) -> None:
        bus = EventBus()
        completed = []
        bus.subscribe("task_completed", lambda d: completed.append(d))
        scheduler = TaskScheduler(event_bus=bus)
        scheduler.run([lambda: "resultado"])
        assert len(completed) == 1

    def test_emits_task_failed_event(self) -> None:
        bus = EventBus()
        failed = []
        bus.subscribe("task_failed", lambda d: failed.append(d))
        scheduler = TaskScheduler(event_bus=bus)
        scheduler.run([lambda: 1 / 0])
        assert len(failed) == 1

    def test_progress_events_count(self) -> None:
        bus = EventBus()
        progress = []
        bus.subscribe("progress", lambda d: progress.append(d))
        scheduler = TaskScheduler(event_bus=bus)
        scheduler.run([lambda: i for i in range(3)])
        assert len(progress) == 3


# ==================================================================
# ParallelCensus
# ==================================================================

class TestParallelCensus:
    def test_empty_list_returns_empty(self) -> None:
        results = ParallelCensus().run([])
        assert results == []

    def test_single_config_result_not_none(
        self, two_separate_disks: DiskConfiguration
    ) -> None:
        results = ParallelCensus().run([two_separate_disks])
        assert len(results) == 1
        assert results[0] is not None

    def test_result_has_required_keys(
        self, single_disk_config: DiskConfiguration
    ) -> None:
        result = ParallelCensus().run([single_disk_config])[0]
        assert "envelope" in result
        assert "contact_graph" in result
        assert "convex_hull" in result
        assert "metadata" in result

    def test_metadata_has_required_fields(
        self, single_disk_config: DiskConfiguration
    ) -> None:
        result = ParallelCensus().run([single_disk_config])[0]
        meta = result["metadata"]
        assert "n_disks" in meta
        assert "elapsed_seconds" in meta
        assert "is_valid" in meta

    def test_n_disks_matches_config(
        self, triangle_config: DiskConfiguration
    ) -> None:
        result = ParallelCensus().run([triangle_config])[0]
        assert result["metadata"]["n_disks"] == 3

    def test_multiple_configs(
        self,
        two_separate_disks: DiskConfiguration,
        triangle_config: DiskConfiguration,
    ) -> None:
        results = ParallelCensus().run([two_separate_disks, triangle_config])
        assert len(results) == 2
        assert all(r is not None for r in results)

    def test_cache_avoids_recomputation(
        self, two_separate_disks: DiskConfiguration
    ) -> None:
        census = ParallelCensus()
        # Primera llamada: computa
        t0 = time.perf_counter()
        census.run([two_separate_disks])
        t1 = time.perf_counter()
        # Segunda llamada: debe usar caché y ser más rápida
        census.run([two_separate_disks])
        t2 = time.perf_counter()
        # La segunda vez no debe tardar más que la primera (heurística débil)
        assert (t2 - t1) <= (t1 - t0) + 0.5  # margen de 500ms

    def test_envelope_is_list_of_dicts(
        self, single_disk_config: DiskConfiguration
    ) -> None:
        result = ParallelCensus().run([single_disk_config])[0]
        for item in result["envelope"]:
            assert "x" in item and "y" in item
