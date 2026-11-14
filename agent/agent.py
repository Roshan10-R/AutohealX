#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_config():
    with (ROOT / "config.json").open(encoding="utf-8") as file:
        config = json.load(file)
    required = ("api_url", "server_id", "api_key")
    missing = [key for key in required if not config.get(key) or "PASTE_" in str(config.get(key))]
    if missing:
        raise ValueError(f"Configure these agent settings first: {', '.join(missing)}")
    return config


def post(config, path, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        config["api_url"].rstrip("/") + path,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Server-ID": config["server_id"],
            "X-API-Key": config["api_key"],
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def collect():
    output = subprocess.check_output(
        ["bash", str(ROOT / "monitor.sh")], text=True, timeout=15
    )
    return json.loads(output)


def restart_service(service):
    service_name = service.removesuffix(".service")
    if not service_name or not service_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"Invalid systemd service name: {service}")
    completed = subprocess.run(
        ["systemctl", "restart", service],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode:
        reason = completed.stderr.strip() or f"systemctl exited with {completed.returncode}"
        return "failed", reason
    return "success", f"Restarted {service}"


def report_issue(config, issue, title, message, severity, active):
    if issue in active:
        return
    post(config, "/api/agent/alerts", {
        "title": title,
        "message": message,
        "severity": severity,
    })


def remediate_services(config, issue, services, active):
    if issue in active:
        return
    if not services:
        post(config, "/api/agent/healings", {
            "issue": issue,
            "action": "No service restart configured",
            "result": "skipped",
            "details": "Configure an explicit service allowlist in agent/config.json to enable this recovery.",
        })
        return
    for service in services:
        try:
            result, details = restart_service(service)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            result, details = "failed", str(error)
        post(config, "/api/agent/healings", {
            "issue": issue,
            "action": f"Restart service: {service}",
            "result": result,
            "details": details,
        })


def check_and_report(config, metrics, active):
    thresholds = config.get("thresholds", {})
    remediation = config.get("remediation", {})
    issues = {}
    for metric, issue, label in (
        ("cpu_percent", "high_cpu", "High CPU"),
        ("memory_percent", "high_memory", "High memory"),
        ("disk_percent", "disk_pressure", "Disk pressure"),
    ):
        threshold = float(thresholds.get(metric, 100))
        value = float(metrics[metric])
        if value >= threshold:
            issues[issue] = (f"{label}: {value:.1f}% (threshold {threshold:.1f}%)", "warning")

    if metrics.get("nginx_active") is False and "nginx" in config.get("critical_services", []):
        issues["service_nginx"] = ("Critical service nginx is not active.", "critical")

    for issue, (message, severity) in issues.items():
        report_issue(config, issue, issue.replace("_", " ").title(), message, severity, active)
        if issue == "high_cpu":
            remediate_services(config, issue, remediation.get("cpu_restart_services", []), active)
        elif issue == "high_memory":
            remediate_services(config, issue, remediation.get("memory_restart_services", []), active)
        elif issue == "service_nginx":
            if remediation.get("restart_failed_critical_services", False):
                result, details = restart_service("nginx")
            else:
                result, details = "skipped", "Critical-service restart is disabled in agent config."
            post(config, "/api/agent/healings", {
                "issue": issue,
                "action": "Restart service: nginx",
                "result": result,
                "details": details,
            })
        elif issue == "disk_pressure" and issue not in active:
            post(config, "/api/agent/healings", {
                "issue": issue,
                "action": "Disk cleanup",
                "result": "skipped",
                "details": "Automatic deletion is disabled; inspect disk usage and configure a safe cleanup policy.",
            })
    active.clear()
    active.update(issues)


def run():
    config = load_config()
    interval = max(10, int(config.get("interval_seconds", 30)))
    active = set()
    print(f"AutoHealX agent started for server {config['server_id']}", flush=True)
    while True:
        started = time.monotonic()
        try:
            metrics = collect()
            post(config, "/api/agent/heartbeat", {
                "agent_version": "1.0.0",
                "hostname": metrics.get("hostname"),
                "platform": metrics.get("platform"),
            })
            post(config, "/api/agent/metrics", {
                key: metrics[key]
                for key in ("cpu_percent", "memory_percent", "disk_percent", "nginx_active")
            })
            check_and_report(config, metrics, active)
            print("Heartbeat and metrics sent.", flush=True)
        except (OSError, ValueError, KeyError, urllib.error.URLError, subprocess.SubprocessError) as error:
            print(f"Agent cycle failed: {error}", flush=True)
        time.sleep(max(0, interval - (time.monotonic() - started)))


if __name__ == "__main__":
    run()
