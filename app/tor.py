import subprocess
import time
from stem import Signal
import stem
from stem.control import Controller

# Path to the Tor executable
TOR_PATH = r"C:\Program Files (x86)\Tor Browser\Browser\TorBrowser\Tor\tor.exe"
TOR_RUNNING = False

# Function to run a command as a specific user using subprocess
def run_as_admin(command):
    global TOR_RUNNING
    if TOR_RUNNING:
        return True
    try:
        # check if the tor process is already running
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate("@kavya123.")
                print("Tor is already running.")
                TOR_RUNNING = True
                return True
        except stem.SocketError:
            print("Tor is not running. Starting Tor...")
        # Run the Tor process as the 'morakhiya' user using subprocess
        subprocess.run(
    ['runas', '/user:kavya', '/savecred', command],
    check=True
)
        print("Tor is starting...")
    except subprocess.CalledProcessError as e:
        print(f"Error starting Tor: {e}")

# Function to wait for Tor to connect fully (bootstrapped 100%)
def wait_for_tor_connection():
    """Wait until Tor is fully bootstrapped (100%)"""
    # Try to connect to Tor's control port until successful
    while True:
        try:
            with Controller.from_port(port=9051) as controller:
                # Use the password to authenticate
                controller.authenticate("@kavya123.")  # Authenticate with Tor control port
                print("Authenticated with Tor Controller.")
                
                # Poll until Tor is fully bootstrapped (100%)
                while True:
                    status = controller.get_info("status/bootstrap-phase")
                    print(f"Tor bootstrapping status: {status}")
                    if "100" in status:
                        print("Tor has successfully bootstrapped 100% and is ready.")
                        TOR_RUNNING = True
                        return
                    time.sleep(1)  # Wait 1 second before checking again
        except stem.SocketError as e:
            print(f"Error connecting to Tor control port: {e}")
            print("Waiting for Tor to be fully ready...")
            time.sleep(2)  # Wait before trying again

def renew_ip():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password='@kavya123.')  # Tor control password
            controller.signal(Signal.NEWNYM)  # Request a new Tor circuit
            time.sleep(5)  # Wait for the new circuit to establish
            print("New IP address requested through Tor.")
    except Exception as e:
        print(f"Error renewing Tor IP: {e}")

            
# Function to make requests through Tor
def make_request_through_tor(session,url = "http://httpbin.org/ip", headers=None, data=None, cookies=None, post = False, json = None, stream = False):
    run = run_as_admin(TOR_PATH)
    if run == True:
        pass
    else:
        wait_for_tor_connection()
    if session is None:
        raise ValueError("Session cannot be None.")
    
    # Ensure the session is set up for Tor proxy (do this only once during session initialization)
    if not hasattr(session, 'tor_proxy_set'):  # Check if the proxy has been set
        session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',  # Default Tor SOCKS5 proxy
            'https': 'socks5h://127.0.0.1:9050',
        }
        session.tor_proxy_set = True  # Mark that the proxy has been set

    response = session.get(f'{url}', headers=headers, cookies=cookies,stream = stream) if not post else session.post(f'{url}', headers=headers, data=data, cookies=cookies, json=json, allow_redirects=True)
    return response
