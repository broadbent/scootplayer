from flask import Flask, render_template, jsonify
import threading
import time
import flot

app = Flask(__name__)
report = {'playback': {}, 'download': {}}

@app.route('/')
def homepage():
    return render_template('index.html', playback=report['playback'], download=report['download'], my_variable='nope')

@app.route('/<buffer_>/<metric>')
def data(buffer_, metric):
    if metric not in report[buffer_]:
        print 'i couldnt find ' + metric
    else:
        print 'found ' + metric
    return jsonify({metric: report[buffer_][metric], 'time_elapsed': report[buffer_]['time_elapsed']})

def send_data(obj, data):
    if obj not in report:
        value = {}
        for element in data:
            value[element] = [data[element]]
        report[obj] = value
    else:
        for element in data:
            try:
                report[obj][element].append(data[element])
            except KeyError:
                report[obj][element] = [data[element]]

class myThread (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        app.run()

thread1 = myThread()
thread1.start()

def printer():
    while(True):
        try:
            # print '\n' + str(report['download']['bandwidth'])+ '\n'
            print str(report)
        except KeyError:
            pass
        time.sleep(1)

# thread2 = threading.Thread(target=printer)
# thread2.start()
