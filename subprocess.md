Summary of what was wrong and what was changed:
What was wrong
Multi-line command – With shell=True, the string you passed had real newlines. The shell ran each line as a separate command:
Line 1: ogr2ogr -f PostgreSQL → ran with no dst/src → "1 argument(s) expected"
Line 2: PG:host=... → run as a program name → "not found"
Line 3: path to .shp → run as a program → "Permission denied"
etc.
Argument order – ogr2ogr expects: ogr2ogr [options] <dst_dataset> <src_dataset>. So the PG connection string (destination) must come before the .shp path (source).
What was changed
The command is built as one line so the shell runs a single ogr2ogr invocation.
Order is: options, then destination (PG:...), then source (.shp path), then the rest of the options.
After redeploy/restart, hit POST /import-network/ again; it should run one correct ogr2ogr command.
what is the different and why need to add shell =True, please explain in the chat

Here’s the difference and why shell=True is used here.
subprocess.run(cmd) without shell=True (default)
Python does not start a shell.
The first argument is the program to run (path or name of the executable).
If you pass a string, that whole string is the single executable name.
So with:
subprocess.run("ogr2ogr -f PostgreSQL PG:... file.shp")
Python tries to run an executable literally named "ogr2ogr -f PostgreSQL PG:... file.shp" (including spaces and the rest). There is no such file → FileNotFoundError.
If you pass a list, the first element is the program, the rest are arguments:
subprocess.run(["ogr2ogr", "-f", "PostgreSQL", "PG:...", "file.shp"])
This runs ogr2ogr with the correct arguments. No shell is involved.
So: string + no shell = entire string = one executable path. List + no shell = program + args, no parsing.
subprocess.run(cmd, shell=True)
Python starts a shell (e.g. /bin/sh -c "...").
The string you pass is the full command line the shell will interpret.
The shell does what you do in a terminal: split the line into the program name and arguments (respecting quotes and spaces). So:
subprocess.run('ogr2ogr -f PostgreSQL PG:"host=..." "file.shp" -nln x', shell=True)
runs one command: program ogr2ogr with all those arguments.
So: string + shell=True = “run this command line as if I typed it in a terminal.”
Why we use shell=True here
We build the command as a single string (with spaces and quoted parts like PG:"..." and the path).
We need that string to be parsed like a shell command so that:
ogr2ogr is the program,
-f, PostgreSQL, PG:"host=...", the path, -nln, etc. are its arguments.
With shell=True, the shell does that parsing. Without it, Python would treat the whole string as the executable name.
Alternative: use no shell and pass a list:
subprocess.run([ "ogr2ogr", "-f", "PostgreSQL", "PG:host=postgis user=postgres dbname=gis password=postgres", f"{unzip_dir}/3D Indoor Network.shp", "-nln", "public.network_staging", "-nlt", "LINESTRINGZ", "-lco", "GEOMETRY_NAME=shape", "-t_srs", "EPSG:2326", "-overwrite"], check=True)
Then you don’t need shell=True because Python passes the program and each argument separately. So:
shell=True = “I’m giving you a command line string; run it via a shell.”
No shell + list = “I’m giving you the program and its arguments; run them directly.”
We added shell=True so that the single-string command is executed correctly by the shell; the list form is the other way to avoid the shell.
