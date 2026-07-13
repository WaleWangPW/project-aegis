import json

import scripts.manage_aegis_dashboard_intent_bridge as manager


def test_status_removes_stale_pid_file(monkeypatch, tmp_path):
    pid_file = tmp_path / "bridge.pid"
    pid_file.write_text("999999\n", encoding="utf-8")
    monkeypatch.setattr(manager, "probe_health", lambda host, port: None)
    monkeypatch.setattr(manager, "process_alive", lambda pid: False)

    status = manager.current_status("127.0.0.1", 8080, pid_file=pid_file)

    assert status["status"] == "STOPPED"
    assert status["health_ready"] is False
    assert not pid_file.exists()
    assert status["safety"]["no_order_placement"] is True
    assert status["safety"]["no_trading_webhook"] is True


def test_status_detects_unmanaged_ready_server(monkeypatch, tmp_path):
    pid_file = tmp_path / "missing.pid"
    monkeypatch.setattr(manager, "probe_health", lambda host, port: {"status": "READY"})

    status = manager.current_status("127.0.0.1", 8080, pid_file=pid_file)

    assert status["status"] == "RUNNING_UNMANAGED"
    assert status["pid_alive"] is False
    assert status["health_ready"] is True


def test_start_reuses_ready_server_without_spawning(monkeypatch, tmp_path):
    pid_file = tmp_path / "bridge.pid"
    log_file = tmp_path / "bridge.log"
    monkeypatch.setattr(manager, "probe_health", lambda host, port: {"status": "READY"})

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("ready server should not spawn a new process")

    monkeypatch.setattr(manager.subprocess, "Popen", fail_popen)
    status = manager.start_bridge("127.0.0.1", 8080, pid_file=pid_file, log_file=log_file)

    assert status["status"] == "RUNNING_UNMANAGED"
    assert status["message"] == "Dashboard intent bridge is already serving."


def test_cli_status_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        manager,
        "current_status",
        lambda host, port: {
            "status": "STOPPED",
            "dashboard_url": manager.dashboard_url(host, port),
            "safety": {"simulation_only": True},
        },
    )
    monkeypatch.setattr(manager.sys, "argv", ["manager", "status"])

    assert manager.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "STOPPED"
    assert payload["safety"]["simulation_only"] is True
