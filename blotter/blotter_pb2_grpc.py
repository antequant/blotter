# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from blotter import blotter_pb2 as blotter_dot_blotter__pb2


class BlotterStub(object):
  """
  RPC interface to the Blotter microservice, for sending market data to BigQuery.
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.HealthCheck = channel.unary_unary(
        '/blotter.Blotter/HealthCheck',
        request_serializer=blotter_dot_blotter__pb2.HealthCheckRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.HealthCheckResponse.FromString,
        )
    self.LoadHistoricalData = channel.unary_stream(
        '/blotter.Blotter/LoadHistoricalData',
        request_serializer=blotter_dot_blotter__pb2.LoadHistoricalDataRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.LoadHistoricalDataResponse.FromString,
        )
    self.StartRealTimeData = channel.unary_unary(
        '/blotter.Blotter/StartRealTimeData',
        request_serializer=blotter_dot_blotter__pb2.StartRealTimeDataRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.StartRealTimeDataResponse.FromString,
        )
    self.CancelRealTimeData = channel.unary_unary(
        '/blotter.Blotter/CancelRealTimeData',
        request_serializer=blotter_dot_blotter__pb2.CancelRealTimeDataRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.CancelRealTimeDataResponse.FromString,
        )
    self.SnapshotOptionChain = channel.unary_unary(
        '/blotter.Blotter/SnapshotOptionChain',
        request_serializer=blotter_dot_blotter__pb2.SnapshotOptionChainRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.SnapshotOptionChainResponse.FromString,
        )
    self.StartStreamingOptionChain = channel.unary_unary(
        '/blotter.Blotter/StartStreamingOptionChain',
        request_serializer=blotter_dot_blotter__pb2.StartStreamingOptionChainRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.StartStreamingOptionChainResponse.FromString,
        )
    self.CancelStreamingOptionChain = channel.unary_unary(
        '/blotter.Blotter/CancelStreamingOptionChain',
        request_serializer=blotter_dot_blotter__pb2.CancelStreamingOptionChainRequest.SerializeToString,
        response_deserializer=blotter_dot_blotter__pb2.CancelStreamingOptionChainResponse.FromString,
        )


class BlotterServicer(object):
  """
  RPC interface to the Blotter microservice, for sending market data to BigQuery.
  """

  def HealthCheck(self, request, context):
    """
    Pings the server to check that it is online and ready to accept requests.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def LoadHistoricalData(self, request, context):
    """
    Loads historical bars for a contract, then enqueues one or more jobs to import them into the appropriate BigQuery table.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def StartRealTimeData(self, request, context):
    """
    Subscribes to real-time data for a contract, streaming bars into the appropriate BigQuery table.

    No guarantees are made about the latency of the BigQuery import, so this is not suitable for hard-real-time trading use cases.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def CancelRealTimeData(self, request, context):
    """
    Cancels a previous real-time data subscription. Any outstanding BigQuery uploads will still complete.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def SnapshotOptionChain(self, request, context):
    """
    Loads the option chain for an underlying contract, pulls quotes for every options contract, then enqueues a job to import them into the appropriate BigQuery table.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def StartStreamingOptionChain(self, request, context):
    """
    Streams periodic quotes for the option chain of an underlying contract into the appropriate BigQuery table.

    No guarantees are made about the latency of the BigQuery import, so this is not suitable for hard-real-time trading use cases.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def CancelStreamingOptionChain(self, request, context):
    """
    Cancels a previous real-time data subscription. Any outstanding BigQuery uploads will still complete.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_BlotterServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'HealthCheck': grpc.unary_unary_rpc_method_handler(
          servicer.HealthCheck,
          request_deserializer=blotter_dot_blotter__pb2.HealthCheckRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.HealthCheckResponse.SerializeToString,
      ),
      'LoadHistoricalData': grpc.unary_stream_rpc_method_handler(
          servicer.LoadHistoricalData,
          request_deserializer=blotter_dot_blotter__pb2.LoadHistoricalDataRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.LoadHistoricalDataResponse.SerializeToString,
      ),
      'StartRealTimeData': grpc.unary_unary_rpc_method_handler(
          servicer.StartRealTimeData,
          request_deserializer=blotter_dot_blotter__pb2.StartRealTimeDataRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.StartRealTimeDataResponse.SerializeToString,
      ),
      'CancelRealTimeData': grpc.unary_unary_rpc_method_handler(
          servicer.CancelRealTimeData,
          request_deserializer=blotter_dot_blotter__pb2.CancelRealTimeDataRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.CancelRealTimeDataResponse.SerializeToString,
      ),
      'SnapshotOptionChain': grpc.unary_unary_rpc_method_handler(
          servicer.SnapshotOptionChain,
          request_deserializer=blotter_dot_blotter__pb2.SnapshotOptionChainRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.SnapshotOptionChainResponse.SerializeToString,
      ),
      'StartStreamingOptionChain': grpc.unary_unary_rpc_method_handler(
          servicer.StartStreamingOptionChain,
          request_deserializer=blotter_dot_blotter__pb2.StartStreamingOptionChainRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.StartStreamingOptionChainResponse.SerializeToString,
      ),
      'CancelStreamingOptionChain': grpc.unary_unary_rpc_method_handler(
          servicer.CancelStreamingOptionChain,
          request_deserializer=blotter_dot_blotter__pb2.CancelStreamingOptionChainRequest.FromString,
          response_serializer=blotter_dot_blotter__pb2.CancelStreamingOptionChainResponse.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'blotter.Blotter', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
