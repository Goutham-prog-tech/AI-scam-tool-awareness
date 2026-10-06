# Read automatically by gunicorn when it starts in this folder.
# 1 worker keeps memory low on the free plan (the ML model is loaded once);
# 8 threads let it serve many visitors at the same time.
workers = 1
threads = 8
timeout = 60
keepalive = 5
