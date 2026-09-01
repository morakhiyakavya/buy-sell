import os
import subprocess
import time

# Tor configuration & toggle (Defaults to False unless USE_TOR=true / ENABLE_TOR=1 is set in env)
USE_TOR = os.environ.get('USE_TOR', os.environ.get('ENABLE_TOR', 'false')).lower() in ('true', '1', 'yes')

TOR_AVAILABLE = False
if USE_TOR:
    try:
        from stem import Signal
        import stem
        from stem.control import Controller
        TOR_AVAILABLE = True
    except Exception:
        TOR_AVAILABLE = False

# Path to the Tor executable (optional)
TOR_PATH = r"C:\Program Files (x86)\Tor Browser\Browser\Tor\tor.exe"
TOR_RUNNING = False


def run_as_admin(command):
    global TOR_RUNNING
    if not USE_TOR or not TOR_AVAILABLE:
        return False
    if TOR_RUNNING:
        return True
    try:
        if os.path.exists(command):
            try:
                with Controller.from_port(port=9051) as controller:
                    controller.authenticate("@kavya123.")
                    print("Tor is already running.")
                    TOR_RUNNING = True
                    return True
            except Exception:
                print("Tor is not running. Starting Tor...")
        else:
            print(f"Tor executable not found at {command}. Disabling Tor.")
            return False

        subprocess.run(
            ['runas', '/user:kavya', '/savecred', command],
            check=True
        )
        print("Tor is starting...")
        return True
    except Exception as e:
        print(f"Error starting Tor: {e}")
        return False


def wait_for_tor_connection():
    """Wait until Tor is fully bootstrapped (100%)"""
    if not USE_TOR or not TOR_AVAILABLE:
        print("wait_for_tor_connection: Tor is disabled or unavailable in this environment")
        return
    attempts = 0
    while attempts < 10:
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate("@kavya123.")
                print("Authenticated with Tor Controller.")
                for _ in range(5):
                    status = controller.get_info("status/bootstrap-phase")
                    print(f"Tor bootstrapping status: {status}")
                    if "100" in status:
                        print("Tor has successfully bootstrapped 100% and is ready.")
                        global TOR_RUNNING
                        TOR_RUNNING = True
                        return
                    time.sleep(1)
        except Exception as e:
            attempts += 1
            print(f"Error connecting to Tor control port: {e}")
            time.sleep(1)
    print("Failed to establish Tor connection. Continuing without Tor.")


LAST_RENEW_TIME = 0


def renew_ip():
    global LAST_RENEW_TIME
    if not USE_TOR or not TOR_AVAILABLE:
        print("renew_ip: Tor is disabled or unavailable in this environment")
        return
    current_time = time.time()
    if current_time - LAST_RENEW_TIME < 10:
        print(f"Skipping IP renewal; last renewal was {current_time - LAST_RENEW_TIME:.1f}s ago.")
        return
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password='@kavya123.')
            controller.signal(Signal.NEWNYM)
            time.sleep(5)
            print("New IP address requested through Tor.")
            LAST_RENEW_TIME = time.time()
    except Exception as e:
        print(f"Error renewing Tor IP: {e}")


def make_request_through_tor(session, url="http://httpbin.org/ip", headers=None, data=None, cookies=None, post=False, json=None, stream=False, allow_redirects=True):
    if session is None:
        raise ValueError("Session cannot be None.")

    # Fallback to direct HTTP request when Tor is disabled or not available
    if not USE_TOR or not TOR_AVAILABLE:
        if post:
            return session.post(url, headers=headers, data=data, cookies=cookies, json=json, allow_redirects=allow_redirects)
        return session.get(url, headers=headers, cookies=cookies, stream=stream, allow_redirects=allow_redirects)

    try:
        run = run_as_admin(TOR_PATH)
        if not run:
            wait_for_tor_connection()

        if not hasattr(session, 'tor_proxy_set'):
            session.proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050',
            }
            session.tor_proxy_set = True

        if post:
            return session.post(url, headers=headers, data=data, cookies=cookies, json=json, allow_redirects=allow_redirects)
        return session.get(url, headers=headers, cookies=cookies, stream=stream, allow_redirects=allow_redirects)
    except Exception as e:
        print(f"Tor request failed ({e}); falling back to direct request.")
        if post:
            return session.post(url, headers=headers, data=data, cookies=cookies, json=json, allow_redirects=allow_redirects)
        return session.get(url, headers=headers, cookies=cookies, stream=stream, allow_redirects=allow_redirects)

