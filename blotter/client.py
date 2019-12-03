from . import blotter_pb2_grpc

import grpc


def new_test_client(port: int, host: str = "localhost") -> blotter_pb2_grpc.BlotterStub:
    channel = grpc.insecure_channel(f"{host}:{port}")
    return blotter_pb2_grpc.BlotterStub(channel)
