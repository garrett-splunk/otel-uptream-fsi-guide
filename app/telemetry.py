"""Upstream OpenTelemetry SDK setup. No Splunk-specific code lives here.

Where the data goes is decided ONLY by environment variables, so the exact same
code runs in "SDK direct" mode and "via Collector" mode:

  OTEL_EXPORTER_OTLP_PROTOCOL          http/protobuf
  OTEL_EXPORTER_OTLP_TRACES_ENDPOINT   full URL, used as-is
  OTEL_EXPORTER_OTLP_METRICS_ENDPOINT  full URL, used as-is
  OTEL_EXPORTER_OTLP_HEADERS           X-SF-Token=<token> (direct mode only)
  OTEL_SERVICE_NAME, OTEL_RESOURCE_ATTRIBUTES (deployment.environment=...)
"""
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

REDACT_IN_SDK = os.environ.get("REDACT_IN_SDK", "false").lower() == "true"
MASK = "***REDACTED***"


def init():
    resource = Resource.create()  # reads OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15000)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))


def tag_sensitive(span, key, value):
    """Set an attribute that should never leave the network in clear text.

    In SDK-direct mode the app itself must mask it (REDACT_IN_SDK=true).
    In Collector mode the Collector deletes the key, so the app can stay simple.
    """
    span.set_attribute(key, MASK if REDACT_IN_SDK else value)
