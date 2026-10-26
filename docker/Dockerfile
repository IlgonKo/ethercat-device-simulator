# Runtime packaging of a previously built Linux executable and model snapshot.
# Rebuild the binary using scripts/linux/build-cmmt.sh before packaging changes.
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}
ARG DEVICE_SIMULATOR_BINARY=build/timing/cmmt_simulator
ARG MODEL_SOURCE=build/model-source-da0b0a3
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/simulator
COPY --chmod=755 ${DEVICE_SIMULATOR_BINARY} /opt/simulator/bin/cmmt_simulator
COPY ${MODEL_SOURCE}/device /opt/model/device
COPY ${MODEL_SOURCE}/configuration /opt/model/configuration
COPY ${MODEL_SOURCE}/motion_server /opt/model/motion_server
COPY ${MODEL_SOURCE}/ethercat /opt/model/ethercat
COPY ${MODEL_SOURCE}/Reference/cmmt_error_catalog.json /opt/model/Reference/cmmt_error_catalog.json
COPY simulator /opt/simulator/simulator
COPY docker/service.py /opt/simulator/docker/service.py
RUN python3 -c "import ctypes; ctypes.CDLL('libstdc++.so.6')" \
    && ldd /opt/simulator/bin/cmmt_simulator \
    && sha256sum /opt/simulator/bin/cmmt_simulator > /opt/simulator/binary.sha256
ENTRYPOINT ["python3", "/opt/simulator/docker/service.py"]
