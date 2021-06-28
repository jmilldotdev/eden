import os
import json
import uvicorn
import traceback
from fastapi import FastAPI, BackgroundTasks

from .log_utils import Colors
from uvicorn.config import LOGGING_CONFIG
from .utils import parse_for_taking_request, write_json, make_filename_and_id, get_filename_from_id, load_json
from .datatypes import Image
from .models import Credentials

def host_block(block,  port = 8080, results_dir = 'results'):

    if not os.path.isdir(results_dir):
        print("[" + Colors.CYAN+ "EDEN" +Colors.END+ "]", "Folder: '"+ results_dir+ "' does not exist, running mkdir")
        os.mkdir(results_dir)

    app =  FastAPI()

    @app.get('/setup')
    def setup():
        try:
            block.__setup__()
            return {
                'status': 'complete'
            }
        except Exception as e: 
            return {
                'ERROR': str(e) 
            }


    def run(args, filename):
        args = dict(args)
        args = parse_for_taking_request(args)
        try:
            output = block.__run__(args)
            for key, value in output.items():
                if isinstance(value, Image):
                    output[key] = value.__call__()

            write_json(dictionary = output,  path = filename)

        except Exception as e:
            traceback.print_exc()
            return {
                "ERROR" : str(e) + ". Check Host's logs for full traceback"
            }

    @app.post('/run')
    def start_run(args: block.data_model, background_tasks: BackgroundTasks):
        filename, token = make_filename_and_id(results_dir = results_dir, username = args.username)

        status = {
            'status': 'running',
            'token': token
        }

        write_json(
            dictionary = status,  
            path = filename
        )

        background_tasks.add_task(run, args = args, filename =filename)
        return status 

    @app.post('/fetch')
    def fetch(credentials: Credentials):

        token = credentials.token
        file_path = get_filename_from_id(results_dir = results_dir, id = token)

        if os.path.exists(file_path):
            results = load_json(file_path)

            if results != {'status': 'running','token': token}:
                return {
                    'status': 'completed',
                    'output': results 
                }
            else:
                return {
                    'status': 'running',
                }

        else:
            return {
                'ERROR': 'invalid token: ' + token
            }

    ## overriding the boring old [INFO] thingy
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "[" + Colors.CYAN+ "EDEN" +Colors.END+ "] %(asctime)s %(message)s"
    LOGGING_CONFIG["formatters"]["access"]["fmt"] = "[" + Colors.CYAN+ "EDEN" +Colors.END+ "] %(levelprefix)s %(client_addr)s - '%(request_line)s' %(status_code)s"
    uvicorn.run(app, port = port)