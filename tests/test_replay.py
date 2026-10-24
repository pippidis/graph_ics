"""Replay records actual mutations, independently of growth batches and fonts."""
from dataclasses import replace
from pathlib import Path
import json
import cairo
import pytest
from graph_ics import Graph, GrowthSettings, CoverageSettings, Text, AngleSettings, Colony, ColonySettings, Interaction, export_graph
from graph_ics import EventLog, EventRecorder, Playback, ReplayRenderer, LiveGrowth
from graph_ics.replay import Event


def make_graph() -> Graph:
    graph = Graph(target_nodes=70, target_seed_nodes=12, target_extra_edges=3, seed=7, angles=AngleSettings(30, 60, 0.6))
    graph.growth(settings=GrowthSettings(coverage=CoverageSettings(tile_size=20), failures_per_parent=5, refill_passes=2, refill_attempts=80, loop_attempts=60))
    return graph


@pytest.mark.parametrize('batch', [1, 17, 1000])
def test_batch_independent_order_and_replay(batch: int, tmp_path: Path) -> None:
    expected = make_graph()
    with EventRecorder(expected) as first: expected.build()
    graph = make_graph()
    destination = tmp_path/'events.jsonl'
    with EventRecorder(graph, path=destination) as recorder:
        while not graph.growth().done: graph.growth().step(batch)
    assert recorder.snapshot().events == first.snapshot().events
    loaded = EventLog.load(destination)
    assert loaded.events == recorder.snapshot().events
    state = loaded.validate()
    assert tuple(state.nodes) == tuple(n.id for n in graph.nodes)
    assert state.parents == graph.parents
    assert {(e.start_node.id, e.end_node.id) for e in state.edges} == {(e.start_node.id, e.end_node.id) for e in graph.edges}
    assert any(event.kind == 'remove' for event in loaded.events)
    assert any(event.kind == 'loop' for event in loaded.events)
    assert state.status == graph.growth().status.value
    loaded.save(tmp_path/'saved.jsonl')
    assert EventLog.load(tmp_path/'saved.jsonl').events == loaded.events


@pytest.mark.parametrize('frame', ['region', 'artwork'])
def test_final_frame_pixel_identity_and_seek(frame: str, tmp_path: Path) -> None:
    from typing import Literal, cast
    graph = Graph(target_nodes=45, seed=4, draw_border=True, texts=(Text('Ag', 50, 50, size=18, padding=4, align='center'),))
    with EventRecorder(graph) as recorder: graph.build()
    path = tmp_path/'scene.jsonl'
    recorder.snapshot().save(path)
    log = EventLog.load(path)
    playback = Playback(log, seconds_per_event=0.05)
    renderer = ReplayRenderer(playback, scale=2, margin=7, background='#101318', frame=cast(Literal['region', 'artwork'], frame))
    final = renderer.render(playback.duration)
    export_graph(graph, tmp_path/'static.png', scale=2, margin=7, background='#101318', frame=cast(Literal['region', 'artwork'], frame))
    static = cairo.ImageSurface.create_from_png(str(tmp_path/'static.png'))
    assert final.get_width() == static.get_width() and final.get_height() == static.get_height()
    assert bytes(final.get_data()) == bytes(static.get_data())
    renderer.render(playback.duration/3)
    assert renderer.cache_rebuilds == 2
    assert bytes(renderer.render(playback.duration).get_data()) == bytes(final.get_data())


def test_clock_partial_edge_and_sequence(tmp_path: Path) -> None:
    graph = Graph(target_nodes=3, seed=1)
    with EventRecorder(graph) as recorder: graph.build()
    clock = Playback(recorder.snapshot(), seconds_per_event=1)
    clock.pause()
    assert clock.advance(10) == 0
    clock.resume()
    clock.speed = 2
    assert clock.advance(0.5) == 1
    renderer = ReplayRenderer(clock)
    halfway = renderer.render(1.5)
    later = renderer.render(1.9)
    assert bytes(halfway.get_data()) != bytes(later.get_data())
    assert len(renderer.state.nodes) == 1  # Endpoint has not yet been committed.
    before = clock.position
    paths = renderer.export_sequence(tmp_path/'frames', fps=2)
    assert len(paths) == 7 and clock.position == before
    assert bytes(cairo.ImageSurface.create_from_png(str(paths[-1])).get_data()) == bytes(renderer.render(clock.duration).get_data())
    with pytest.raises(FileExistsError): renderer.export_sequence(tmp_path/'frames', fps=2)
    with pytest.raises(ValueError): renderer.export_sequence(tmp_path/'too_many', fps=100, max_frames=2)
    with pytest.raises(ValueError): clock.seek(-1)
    with pytest.raises(ValueError): clock.speed = 0


def test_join_ownership_and_stream_only(tmp_path: Path) -> None:
    colonies = ColonySettings((Colony('a', ((30, 50),)), Colony('b', ((70, 50),))), (Interaction('a', 'b', allow_join=True),), target_bridges=1, bridge_distance=80)
    graph = Graph(target_nodes=2, colonies=colonies, edge_length_max=40, seed=0)
    with EventRecorder(graph, path=tmp_path/'stream.jsonl', retain=False) as recorder: graph.build()
    assert recorder.events == []
    with pytest.raises(ValueError): recorder.snapshot()
    log = EventLog.load(tmp_path/'stream.jsonl')
    assert [event.kind for event in log.events] == ['seed', 'seed', 'join', 'complete']
    state = log.validate()
    assert {node.colony_id for node in state.nodes.values()} == {'a', 'b'}
    assert all(parent is None for parent in state.parents.values())
    assert state.network.number_of_edges() == 1


def test_live_pause_deadline_and_append() -> None:
    graph = Graph(target_nodes=20, seed=4)
    live = LiveGrowth(graph)
    assert live.recorder is not None
    renderer = ReplayRenderer(Playback(live.recorder.snapshot()))
    live.pause()
    assert live.tick(100) == () and graph.growth().attempts == 0
    live.resume()
    assert live.tick(100, time_budget_ms=0) == ()
    assert sum(result.attempts for result in live.tick(3, time_budget_ms=1000)) <= 3
    while not graph.growth().done:
        live.tick(7)
        renderer.update(live.recorder.snapshot())
        renderer.render(renderer.playback.duration)
    assert len(renderer.state.nodes) == len(graph.nodes)
    live.close()
    assert graph._event_listener is None
    assert live.tick() == ()
    with pytest.raises(ValueError): live.tick(0)
    with pytest.raises(ValueError): live.tick(time_budget_ms=-1)


def test_cancellation_empty_and_malformed_logs(tmp_path: Path) -> None:
    graph = Graph(target_nodes=1, seed=4)
    with EventRecorder(graph) as recorder: graph.growth().cancel()
    assert recorder.snapshot().validate().status == 'cancelled'
    renderer = ReplayRenderer(Playback(recorder.snapshot()))
    assert renderer.render().get_width() > 0
    log = recorder.snapshot()
    with pytest.raises(ValueError): replace(log, version=2).validate()
    with pytest.raises(ValueError): replace(log, events=(Event('remove', removed=('missing',)),)).validate()
    with pytest.raises(ValueError): replace(log, events=log.events+(Event('seed'),)).validate()
    path = tmp_path/'invalid.jsonl'
    path.write_text(json.dumps({'version': 99})+'\n')
    with pytest.raises(ValueError): EventLog.load(path)
    path.write_text('{}\n')
    with pytest.raises(ValueError): EventLog.load(path)
    with pytest.raises(ValueError): EventRecorder(Graph(), retain=False)
    with pytest.raises(ValueError): EventRecorder(graph)


def test_recording_is_optional_and_reset_detaches() -> None:
    graph = Graph(target_nodes=10, seed=5)
    live = LiveGrowth(graph, record=False)
    while not live.generator.done: live.tick(10)
    assert graph._event_listener is None
    fresh = Graph(target_nodes=10, seed=5)
    recorder = EventRecorder(fresh)
    with pytest.raises(ValueError): EventRecorder(fresh)
    fresh.build()
    fresh.build(force=True)
    assert fresh._event_listener is None
    recorder.close()
    assert [(n.center.x, n.center.y) for n in fresh.nodes] == [(n.center.x, n.center.y) for n in graph.nodes]



def test_saturated_live_attempts_remain_bounded() -> None:
    from shapely.geometry import box
    graph = Graph(target_nodes=1000, outline_polygon=box(0, 0, 1, 1), seed=0)
    graph.growth(settings=GrowthSettings(seed_attempts=9))
    live = LiveGrowth(graph)
    while not live.generator.done:
        results = live.tick(2)
        assert sum(result.attempts for result in results) <= 2
    assert live.generator.attempts == 9 and not graph.nodes
    assert live.recorder is not None and live.recorder.snapshot().validate().status == 'frontier_exhausted'
    live.close()


def test_loaded_text_never_remeasures_fonts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    graph = Graph(target_nodes=0, texts=(Text('Saved paths', 10, 40),))
    with EventRecorder(graph) as recorder: graph.build()
    recorder.snapshot().save(tmp_path/'text.jsonl')
    def forbidden_measurement(self: Text) -> None:
        raise AssertionError('Playback must not measure fonts')
    monkeypatch.setattr(Text, 'measure', forbidden_measurement)
    log = EventLog.load(tmp_path/'text.jsonl')
    assert ReplayRenderer(Playback(log)).render().get_width() > 0


def test_transparent_final_and_recorded_cancel_cleanup(tmp_path: Path) -> None:
    from graph_ics import Node
    graph = Graph(target_nodes=2, input_nodes=[Node(20, 20), Node(80, 80)])
    with EventRecorder(graph) as recorder: graph.growth().cancel()
    log = recorder.snapshot()
    assert [event.kind for event in log.events] == ['seed', 'seed', 'remove', 'complete']
    clock = Playback(log)
    surface = ReplayRenderer(clock).render(clock.duration)
    assert not any(bytes(surface.get_data()))
    log.save(tmp_path/'cleanup.jsonl')
    assert not EventLog.load(tmp_path/'cleanup.jsonl').validate().nodes


def test_invalid_path_and_live_replacement() -> None:
    graph = Graph(target_nodes=3, seed=1)
    with EventRecorder(graph) as recorder: graph.build()
    log = recorder.snapshot()
    renderer = ReplayRenderer(Playback(log))
    with pytest.raises(ValueError): renderer.update(replace(log, events=log.events[:-1]))
    with pytest.raises(ValueError): replace(log, scene=replace(log.scene, minimum_scale=float('nan'))).validate()
    with pytest.raises(ValueError): Playback(log, seconds_per_event=0)
    with pytest.raises(ValueError): ReplayRenderer(Playback(log), scale=0)



def test_field_configuration_and_callback_free_replay(tmp_path: Path) -> None:
    from graph_ics import SpatialFields, ConstantField, ImageField, CallableField
    calls = 0
    def thickness(x: float, y: float) -> float:
        nonlocal calls
        calls += 1
        return 1
    fields = SpatialFields(radius=ConstantField(1.2), length=ImageField(((1.0, 1.5), (1.0, 1.5)), (0, 0, 100, 100)), thickness=CallableField(thickness))
    graph = Graph(target_nodes=10, fields=fields, seed=4)
    with EventRecorder(graph) as recorder: graph.build()
    before = calls
    recorder.snapshot().save(tmp_path/'fields.jsonl')
    log = EventLog.load(tmp_path/'fields.jsonl')
    assert len(log.validate().nodes) == len(graph.nodes) and calls == before
    assert log.scene.configuration['fields']['radius']['parameters']['value'] == 1.2
    assert log.scene.configuration['fields']['length']['parameters']['pixels'] == [[1.0, 1.5], [1.0, 1.5]]
    assert log.scene.configuration['fields']['thickness']['type'] == 'CallableField'
