import argparse
import json
import os
from contextlib import ExitStack
from functional_model.configuration import load_config, load_environment
from functional_model.storage.parameter_store import ParameterStore
from functional_model.diagnostics.python_timing import PythonTiming
from functional_model.runtime.axis import Model
from functional_model.runtime.fleet import ModelFleet
from device_descriptions.cmmt_as.fixture import generate_fixture
from functional_model.ipc.server import serve

def main():
    p=argparse.ArgumentParser()
    source = p.add_mutually_exclusive_group()
    source.add_argument('--env-file')
    source.add_argument('--environment', action='store_true')
    p.add_argument('--fixture-dir')
    p.add_argument('--socket')
    p.add_argument('--timing', action='store_true')
    args=p.parse_args()
    if not args.fixture_dir and not args.socket:p.error('Specify --fixture-dir or --socket')
    with ExitStack() as stack:
        if args.env_file or args.environment:
            config = load_config(args.env_file) if args.env_file else load_environment(os.environ)
            store = stack.enter_context(ParameterStore(config['storage']['directory']))
            model = ModelFleet(config, store)
            if args.fixture_dir: model.generate_fixture(args.fixture_dir)
        else:
            # Explicit original one-axis feasibility harness, without persistence.
            model = Model()
            if args.fixture_dir: generate_fixture(model,args.fixture_dir)
        print(json.dumps(model.describe()), flush=True)
        timing = None
        if args.timing:
            models = model.models if isinstance(model, ModelFleet) else [model]
            timing = PythonTiming(len(models))
            for item in models: item.timing = timing
        if args.socket: serve(model,args.socket,timing)



if __name__=='__main__':main()
