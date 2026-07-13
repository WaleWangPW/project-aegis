import json

import scripts.manage_aegis_dashboard_intent_bridge as manager


def test_status_removes_stale_pid_file(monkeypatch, tmp_path):
    pid_file = tmp_path / "bridge.pid"
    meta_file = tmp_path / "bridge.meta.json"
    pid_file.write_text("999999\n", encoding="utf-8")
    meta_file.write_text('{"bind_host":"127.0.0.1"}\n', encoding="utf-8")
    monkeypatch.setattr(manager, "probe_health", lambda host, port: None)
    monkeypatch.setattr(manager, "process_alive", lambda pid: False)

    status = manager.current_status("127.0.0.1", 8080, pid_file=pid_file, meta_file=meta_file)

    assert status["status"] == "STOPPED"
    assert status["health_ready"] is False
    assert not pid_file.exists()
    assert not meta_file.exists()
    assert status["safety"]["no_order_placement"] is True
    assert status["safety"]["no_trading_webhook"] is True


def test_status_detects_unmanaged_ready_server(monkeypatch, tmp_path):
    pid_file = tmp_path / "missing.pid"
    meta_file = tmp_path / "missing.meta.json"
    monkeypatch.setattr(manager, "probe_health", lambda host, port: {"status": "READY"})

    status = manager.current_status("127.0.0.1", 8080, pid_file=pid_file, meta_file=meta_file)

    assert status["status"] == "RUNNING_UNMANAGED"
    assert status["pid_alive"] is False
    assert status["health_ready"] is True


def test_lan_status_uses_local_health_probe(monkeypatch, tmp_path):
    pid_file = tmp_path / "missing.pid"
    meta_file = tmp_path / "missing.meta.json"
    meta_file.write_text('{"bind_host":"0.0.0.0","port":8080}\n', encoding="utf-8")
    seen = []

    def fake_urlopen(url, timeout=1.0):
        seen.append(url)

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b'{"status":"READY"}'

        return Response()

    monkeypatch.setattr(manager.urllib.request, "urlopen", fake_urlopen)
    status = manager.current_status("0.0.0.0", 8080, pid_file=pid_file, meta_file=meta_file)

    assert status["status"] == "RUNNING_UNMANAGED"
    assert seen == ["http://127.0.0.1:8080/api/dashboard-intents/health"]
    assert status["access"]["bind_host"] == "0.0.0.0"
    assert status["access"]["lan_enabled"] is True
    assert status["dashboard_url"] == "http://127.0.0.1:8080/dashboard/index.html"


def test_start_reuses_ready_server_without_spawning(monkeypatch, tmp_path):
    pid_file = tmp_path / "bridge.pid"
    meta_file = tmp_path / "bridge.meta.json"
    log_file = tmp_path / "bridge.log"
    meta_file.write_text('{"bind_host":"127.0.0.1","port":8080}\n', encoding="utf-8")
    monkeypatch.setattr(manager, "probe_health", lambda host, port: {"status": "READY"})

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("ready server should not spawn a new process")

    monkeypatch.setattr(manager.subprocess, "Popen", fail_popen)
    status = manager.start_bridge("127.0.0.1", 8080, pid_file=pid_file, meta_file=meta_file, log_file=log_file)

    assert status["status"] == "RUNNING_UNMANAGED"
    assert status["message"] == "Dashboard intent bridge is already serving."


def test_start_lan_requires_stop_when_local_bridge_is_ready(monkeypatch, tmp_path):
    pid_file = tmp_path / "bridge.pid"
    meta_file = tmp_path / "bridge.meta.json"
    log_file = tmp_path / "bridge.log"
    meta_file.write_text('{"bind_host":"127.0.0.1","port":8080}\n', encoding="utf-8")
    monkeypatch.setattr(manager, "probe_health", lambda host, port: {"status": "READY"})

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("bind mode switch should not spawn a new process")

    monkeypatch.setattr(manager.subprocess, "Popen", fail_popen)
    status = manager.start_bridge("0.0.0.0", 8080, pid_file=pid_file, meta_file=meta_file, log_file=log_file)

    assert status["health_ready"] is True
    assert status["bind_host_matches_request"] is False
    assert "dashboard-stop" in status["message"]


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
