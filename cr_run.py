import os, subprocess, shlex
import sys, signal
import time, urllib2

appserver_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "sdk/python/dev_appserver.py"
)
datastore_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "mydatastore"
)
launch_string = "python {0} app --skip_sdk_update_check YES --datastore_path={1}".format(
    appserver_path,
    datastore_path
)
stdout = os.path.abspath('stdout.log')
stderr = os.path.abspath('stderr.log')
stdout_fh = open(stdout, 'w')
stderr_fh = open(stderr, 'w')
p = subprocess.Popen(
    shlex.split(launch_string),
    stdout=stdout_fh,
    stderr=stderr_fh
)
# Wait for server to launch
server_up = False
for attempt_number in range(0, 20):
    try:
        req = urllib2.urlopen("http://localhost:8080/login")
    except Exception:
        req = None
    if req and req.getcode() == 200:
        # Make sure process hasnt terminated, otherwise might be
        # another webserver.
        time.sleep(3)
        if p.poll() is None:
            server_up = True
        else:
            print "There seems to be another webserver already running on localhost:8080"
            server_up = False
        break
    print "Checking if launched -- try " + str(attempt_number + 1) +" of 20"
    # Sleep for some time in between requests
    time.sleep(5)

if server_up:
    print "Server launched successfully! Running with process identifier: {0}".format(
        p.pid
    )
    print "Logs can be found in", stdout, "and", stderr
    print "Press ctrl+c to kill the server..."

    def signal_handler(signal, frame):
        print "Killing web server..."
        p.terminate()
        print "Done."
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    signal.pause()
else:
    print "Server failed to launch."
    print "Check the logs at", stdout, "and", stderr
