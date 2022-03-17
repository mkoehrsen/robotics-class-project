Root directory for code intended to run on the vehicle. 

# Arduino

The `arduino` subdirectory has the arduino code for motor control, using firmata just to simplify communication slightly. The `Makefile` in this directory can be used to compile the arduino code and upload it to the board. See the comment in the `Makefile` for one-time setup notes.

The arduino code has hard-coded pin numbers for motor control. We could make this configurable but it's probably easier to just agree on pin assignments.

# Webapp

The `webapp` subdirectory has a flask app for basic control of the vehicle. The intended way to launch it is using `make run` from this directory. 

Once the webapp is running:

* Visit `http://<hostname>:8080/` for the UI. It allows for controlling travel direction with arrow keys and throttle control with space/shift-space.
* Point a media player at `rtsp://<hostname>:8554/video_stream` to view video from the vehicle. I've been using MPlayerX. It turns out RTSP isn't supported by modern browsers so media player seems like the way to go.

Usually the video shows up initially as gray and then takes as long as 20-30 seconds to display properly. Sometimes it shows up with persistent artifacts but I found that restarting the media player fixes this pretty reliably.
