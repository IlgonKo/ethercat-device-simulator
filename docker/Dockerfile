# Runtime packaging of a previously built Linux executable and model snapshot.
# Rebuild the binary using scripts/linux/build-cmmt.sh before packaging changes.
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}
ARG DEVICE_SIMULATOR_BINARY=build/timing/cmmt_simulator
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/simulator
COPY --chmod=755 ${DEVICE_SIMULATOR_BINARY} /opt/simulator/bin/cmmt_simulator
COPY src/functional_model /opt/simulator/src/functional_model
COPY device_descriptions /opt/simulator/device_descriptions
ENV PYTHONPATH=/opt/simulator/src:/opt/simulator
COPY docker/service.py /opt/simulator/docker/service.py
RUN python3 -c "import ctypes; ctypes.CDLL('libstdc++.so.6')" \
    && ldd /opt/simulator/bin/cmmt_simulator \
    && sha256sum /opt/simulator/bin/cmmt_simulator > /opt/simulator/binary.sha256
ENTRYPOINT ["python3", "/opt/simulator/docker/service.py"]
