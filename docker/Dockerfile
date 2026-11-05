# Both images are locked by digest after input preparation.
ARG BASE_IMAGE=python@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9
ARG BUILDER_IMAGE=python@sha256:17b9724493d916f56565c131f389faff2597f46dec6ce09516f95125bc9f519f
FROM ${BUILDER_IMAGE} AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY docker/requirements-fmi.txt /tmp/requirements-fmi.txt
COPY docker/wheels /tmp/wheels
RUN python3 -m venv /opt/fmi && /opt/fmi/bin/pip install --no-index --find-links=/tmp/wheels -r /tmp/requirements-fmi.txt
ENV PATH=/opt/fmi/bin:$PATH
COPY docker/dependency-inputs.json docker/build-native.py /workspace/docker/
COPY docker/inputs /workspace/docker/inputs
RUN python3 docker/build-native.py
COPY CMakeLists.txt /workspace/
COPY third_party/KickCAT /workspace/third_party/KickCAT
COPY src /workspace/src
COPY device_descriptions /workspace/device_descriptions
COPY tests /workspace/tests
COPY .env.example /workspace/.env.example
COPY docker/service.py /workspace/docker/service.py
RUN cmake -S . -B build/timing -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/deps \
 && cmake --build build/timing --target cmmt_simulator test_fixed_mapping test_multi_slave test_async_fault test_sdo_gateway test_dynamic_mapping test_mapping_store test_mapping_store_failures --parallel 2 \
 && ctest --test-dir build/timing --output-on-failure
COPY scripts /workspace/scripts
RUN python3 scripts/linux/build-copley-fmu.py --source docker/inputs/CopleyDriveSim-source.fmu --output model_artifacts/CopleyDriveSim-linux.fmu
ENV PYTHONPATH=/workspace/src:/workspace
RUN python3 -m unittest discover -s tests/unit -v \
 && COPLEY_TEST_FMU=/workspace/model_artifacts/CopleyDriveSim-linux.fmu python3 -m unittest tests.integration.test_copley_fmu -v \
 && python3 tests/integration/run_dynamic_mapping.py --axes 4 --fmu-dir /workspace/model_artifacts --storage-startup \
 && python3 tests/integration/run_remap_ipc.py --fmu-dir /workspace/model_artifacts \
 && python3 tests/integration/run_dynamic_mapping.py --axes 4 --fmu-dir /workspace/model_artifacts --motion

FROM ${BASE_IMAGE} AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH=/opt/fmi/bin:$PATH
WORKDIR /opt/simulator
COPY --from=builder /opt/fmi /opt/fmi
COPY --from=builder /workspace/build/timing/cmmt_simulator /opt/simulator/bin/cmmt_simulator
COPY --from=builder /workspace/model_artifacts /model_artifacts
COPY --from=builder /workspace/src/functional_model /opt/simulator/src/functional_model
COPY --from=builder /workspace/device_descriptions /opt/simulator/device_descriptions
COPY --from=builder /workspace/docker/service.py /opt/simulator/docker/service.py
ENV PYTHONPATH=/opt/simulator/src:/opt/simulator DEVICE_SIMULATOR_FMU_DIR=/model_artifacts
RUN ! command -v gcc && ! command -v g++ \
 && python3 -c "import ctypes; ctypes.CDLL('libstdc++.so.6')" \
 && ldd /opt/simulator/bin/cmmt_simulator \
 && sha256sum /opt/simulator/bin/cmmt_simulator > /opt/simulator/binary.sha256
ENTRYPOINT ["python3", "/opt/simulator/docker/service.py"]
