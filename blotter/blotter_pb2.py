# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: blotter/blotter.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='blotter/blotter.proto',
  package='blotter',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\x15\x62lotter/blotter.proto\x12\x07\x62lotter\"\xbb\x04\n\x11\x43ontractSpecifier\x12\x0e\n\x06symbol\x18\x01 \x01(\t\x12=\n\x0csecurityType\x18\x02 \x01(\x0e\x32\'.blotter.ContractSpecifier.SecurityType\x12$\n\x1clastTradeDateOrContractMonth\x18\x03 \x01(\t\x12\x0e\n\x06strike\x18\x04 \x01(\t\x12/\n\x05right\x18\x05 \x01(\x0e\x32 .blotter.ContractSpecifier.Right\x12\x12\n\nmultiplier\x18\x06 \x01(\t\x12\x10\n\x08\x65xchange\x18\x07 \x01(\t\x12\x10\n\x08\x63urrency\x18\x08 \x01(\t\x12\x13\n\x0blocalSymbol\x18\t \x01(\t\x12\x17\n\x0fprimaryExchange\x18\n \x01(\t\x12\x14\n\x0ctradingClass\x18\x0b \x01(\t\x12\x16\n\x0eincludeExpired\x18\x0c \x01(\x08\"\xa8\x01\n\x0cSecurityType\x12\t\n\x05STOCK\x10\x00\x12\n\n\x06OPTION\x10\x01\x12\n\n\x06\x46UTURE\x10\x02\x12\t\n\x05INDEX\x10\x03\x12\x12\n\x0e\x46UTURES_OPTION\x10\x04\x12\x08\n\x04\x43\x41SH\x10\x05\x12\x07\n\x03\x43\x46\x44\x10\x06\x12\t\n\x05\x43OMBO\x10\x07\x12\x0b\n\x07WARRANT\x10\x08\x12\x08\n\x04\x42OND\x10\t\x12\r\n\tCOMMODITY\x10\n\x12\x08\n\x04NEWS\x10\x0b\x12\x08\n\x04\x46UND\x10\x0c\"1\n\x05Right\x12\x15\n\x11UNSPECIFIED_RIGHT\x10\x00\x12\x07\n\x03PUT\x10\x01\x12\x08\n\x04\x43\x41LL\x10\x02\"\x88\x01\n\x08\x44uration\x12\r\n\x05\x63ount\x18\x01 \x01(\x05\x12(\n\x04unit\x18\x02 \x01(\x0e\x32\x1a.blotter.Duration.TimeUnit\"C\n\x08TimeUnit\x12\x0b\n\x07SECONDS\x10\x00\x12\x08\n\x04\x44\x41YS\x10\x01\x12\t\n\x05WEEKS\x10\x02\x12\n\n\x06MONTHS\x10\x03\x12\t\n\x05YEARS\x10\x04\"\xd9\x07\n\x19LoadHistoricalDataRequest\x12\x35\n\x11\x63ontractSpecifier\x18\x01 \x01(\x0b\x32\x1a.blotter.ContractSpecifier\x12\x17\n\x0f\x65ndTimestampUTC\x18\x02 \x01(\x03\x12#\n\x08\x64uration\x18\x03 \x01(\x0b\x32\x11.blotter.Duration\x12;\n\x07\x62\x61rSize\x18\x04 \x01(\x0e\x32*.blotter.LoadHistoricalDataRequest.BarSize\x12?\n\tbarSource\x18\x05 \x01(\x0e\x32,.blotter.LoadHistoricalDataRequest.BarSource\x12\x1f\n\x17regularTradingHoursOnly\x18\x06 \x01(\x08\"\x9b\x03\n\x07\x42\x61rSize\x12\x14\n\x10UNSPECIFIED_SIZE\x10\x00\x12\x0e\n\nONE_SECOND\x10\x01\x12\x10\n\x0c\x46IVE_SECONDS\x10\x05\x12\x0f\n\x0bTEN_SECONDS\x10\n\x12\x13\n\x0f\x46IFTEEN_SECONDS\x10\x0f\x12\x12\n\x0eTHIRTY_SECONDS\x10\x1e\x12\x0e\n\nONE_MINUTE\x10<\x12\x0f\n\x0bTWO_MINUTES\x10x\x12\x12\n\rTHREE_MINUTES\x10\xb4\x01\x12\x11\n\x0c\x46IVE_MINUTES\x10\xac\x02\x12\x10\n\x0bTEN_MINUTES\x10\xd8\x04\x12\x14\n\x0f\x46IFTEEN_MINUTES\x10\x84\x07\x12\x13\n\x0eTWENTY_MINUTES\x10\xb0\t\x12\x13\n\x0eTHIRTY_MINUTES\x10\x88\x0e\x12\r\n\x08ONE_HOUR\x10\x90\x1c\x12\x0e\n\tTWO_HOURS\x10\xa0\x38\x12\x10\n\x0bTHREE_HOURS\x10\xb0T\x12\x0f\n\nFOUR_HOURS\x10\xc0p\x12\x11\n\x0b\x45IGHT_HOURS\x10\x80\xe1\x01\x12\r\n\x07ONE_DAY\x10\x80\xa3\x05\x12\x0e\n\x08ONE_WEEK\x10\x80\xf5$\x12\x10\n\tONE_MONTH\x10\x80\x9a\x9e\x01\"\x89\x02\n\tBarSource\x12\x16\n\x12UNSPECIFIED_SOURCE\x10\x00\x12\n\n\x06TRADES\x10\x01\x12\x0c\n\x08MIDPOINT\x10\x02\x12\x07\n\x03\x42ID\x10\x03\x12\x07\n\x03\x41SK\x10\x04\x12\x0b\n\x07\x42ID_ASK\x10\x05\x12\x11\n\rADJUSTED_LAST\x10\x06\x12\x19\n\x15HISTORICAL_VOLATILITY\x10\x07\x12\x1d\n\x19OPTION_IMPLIED_VOLATILITY\x10\x08\x12\x0f\n\x0bREBATE_RATE\x10\t\x12\x0c\n\x08\x46\x45\x45_RATE\x10\n\x12\r\n\tYIELD_BID\x10\x0b\x12\r\n\tYIELD_ASK\x10\x0c\x12\x11\n\rYIELD_BID_ASK\x10\r\x12\x0e\n\nYIELD_LAST\x10\x0e\"\x1c\n\x1aLoadHistoricalDataResponse2j\n\x07\x42lotter\x12_\n\x12LoadHistoricalData\x12\".blotter.LoadHistoricalDataRequest\x1a#.blotter.LoadHistoricalDataResponse\"\x00\x62\x06proto3')
)



_CONTRACTSPECIFIER_SECURITYTYPE = _descriptor.EnumDescriptor(
  name='SecurityType',
  full_name='blotter.ContractSpecifier.SecurityType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='STOCK', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OPTION', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FUTURE', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='INDEX', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FUTURES_OPTION', index=4, number=4,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CASH', index=5, number=5,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CFD', index=6, number=6,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='COMBO', index=7, number=7,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='WARRANT', index=8, number=8,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='BOND', index=9, number=9,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='COMMODITY', index=10, number=10,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NEWS', index=11, number=11,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FUND', index=12, number=12,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=387,
  serialized_end=555,
)
_sym_db.RegisterEnumDescriptor(_CONTRACTSPECIFIER_SECURITYTYPE)

_CONTRACTSPECIFIER_RIGHT = _descriptor.EnumDescriptor(
  name='Right',
  full_name='blotter.ContractSpecifier.Right',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNSPECIFIED_RIGHT', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='PUT', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CALL', index=2, number=2,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=557,
  serialized_end=606,
)
_sym_db.RegisterEnumDescriptor(_CONTRACTSPECIFIER_RIGHT)

_DURATION_TIMEUNIT = _descriptor.EnumDescriptor(
  name='TimeUnit',
  full_name='blotter.Duration.TimeUnit',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SECONDS', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DAYS', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='WEEKS', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MONTHS', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='YEARS', index=4, number=4,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=678,
  serialized_end=745,
)
_sym_db.RegisterEnumDescriptor(_DURATION_TIMEUNIT)

_LOADHISTORICALDATAREQUEST_BARSIZE = _descriptor.EnumDescriptor(
  name='BarSize',
  full_name='blotter.LoadHistoricalDataRequest.BarSize',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNSPECIFIED_SIZE', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ONE_SECOND', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FIVE_SECONDS', index=2, number=5,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TEN_SECONDS', index=3, number=10,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FIFTEEN_SECONDS', index=4, number=15,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='THIRTY_SECONDS', index=5, number=30,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ONE_MINUTE', index=6, number=60,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TWO_MINUTES', index=7, number=120,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='THREE_MINUTES', index=8, number=180,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FIVE_MINUTES', index=9, number=300,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TEN_MINUTES', index=10, number=600,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FIFTEEN_MINUTES', index=11, number=900,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TWENTY_MINUTES', index=12, number=1200,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='THIRTY_MINUTES', index=13, number=1800,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ONE_HOUR', index=14, number=3600,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TWO_HOURS', index=15, number=7200,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='THREE_HOURS', index=16, number=10800,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FOUR_HOURS', index=17, number=14400,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='EIGHT_HOURS', index=18, number=28800,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ONE_DAY', index=19, number=86400,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ONE_WEEK', index=20, number=604800,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ONE_MONTH', index=21, number=2592000,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=1054,
  serialized_end=1465,
)
_sym_db.RegisterEnumDescriptor(_LOADHISTORICALDATAREQUEST_BARSIZE)

_LOADHISTORICALDATAREQUEST_BARSOURCE = _descriptor.EnumDescriptor(
  name='BarSource',
  full_name='blotter.LoadHistoricalDataRequest.BarSource',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNSPECIFIED_SOURCE', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TRADES', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MIDPOINT', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='BID', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ASK', index=4, number=4,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='BID_ASK', index=5, number=5,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ADJUSTED_LAST', index=6, number=6,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='HISTORICAL_VOLATILITY', index=7, number=7,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OPTION_IMPLIED_VOLATILITY', index=8, number=8,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='REBATE_RATE', index=9, number=9,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FEE_RATE', index=10, number=10,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='YIELD_BID', index=11, number=11,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='YIELD_ASK', index=12, number=12,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='YIELD_BID_ASK', index=13, number=13,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='YIELD_LAST', index=14, number=14,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=1468,
  serialized_end=1733,
)
_sym_db.RegisterEnumDescriptor(_LOADHISTORICALDATAREQUEST_BARSOURCE)


_CONTRACTSPECIFIER = _descriptor.Descriptor(
  name='ContractSpecifier',
  full_name='blotter.ContractSpecifier',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='symbol', full_name='blotter.ContractSpecifier.symbol', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='securityType', full_name='blotter.ContractSpecifier.securityType', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='lastTradeDateOrContractMonth', full_name='blotter.ContractSpecifier.lastTradeDateOrContractMonth', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='strike', full_name='blotter.ContractSpecifier.strike', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='right', full_name='blotter.ContractSpecifier.right', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='multiplier', full_name='blotter.ContractSpecifier.multiplier', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='exchange', full_name='blotter.ContractSpecifier.exchange', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='currency', full_name='blotter.ContractSpecifier.currency', index=7,
      number=8, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='localSymbol', full_name='blotter.ContractSpecifier.localSymbol', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='primaryExchange', full_name='blotter.ContractSpecifier.primaryExchange', index=9,
      number=10, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='tradingClass', full_name='blotter.ContractSpecifier.tradingClass', index=10,
      number=11, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='includeExpired', full_name='blotter.ContractSpecifier.includeExpired', index=11,
      number=12, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CONTRACTSPECIFIER_SECURITYTYPE,
    _CONTRACTSPECIFIER_RIGHT,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=35,
  serialized_end=606,
)


_DURATION = _descriptor.Descriptor(
  name='Duration',
  full_name='blotter.Duration',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='count', full_name='blotter.Duration.count', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='unit', full_name='blotter.Duration.unit', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _DURATION_TIMEUNIT,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=609,
  serialized_end=745,
)


_LOADHISTORICALDATAREQUEST = _descriptor.Descriptor(
  name='LoadHistoricalDataRequest',
  full_name='blotter.LoadHistoricalDataRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='contractSpecifier', full_name='blotter.LoadHistoricalDataRequest.contractSpecifier', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='endTimestampUTC', full_name='blotter.LoadHistoricalDataRequest.endTimestampUTC', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='duration', full_name='blotter.LoadHistoricalDataRequest.duration', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='barSize', full_name='blotter.LoadHistoricalDataRequest.barSize', index=3,
      number=4, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='barSource', full_name='blotter.LoadHistoricalDataRequest.barSource', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='regularTradingHoursOnly', full_name='blotter.LoadHistoricalDataRequest.regularTradingHoursOnly', index=5,
      number=6, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _LOADHISTORICALDATAREQUEST_BARSIZE,
    _LOADHISTORICALDATAREQUEST_BARSOURCE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=748,
  serialized_end=1733,
)


_LOADHISTORICALDATARESPONSE = _descriptor.Descriptor(
  name='LoadHistoricalDataResponse',
  full_name='blotter.LoadHistoricalDataResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1735,
  serialized_end=1763,
)

_CONTRACTSPECIFIER.fields_by_name['securityType'].enum_type = _CONTRACTSPECIFIER_SECURITYTYPE
_CONTRACTSPECIFIER.fields_by_name['right'].enum_type = _CONTRACTSPECIFIER_RIGHT
_CONTRACTSPECIFIER_SECURITYTYPE.containing_type = _CONTRACTSPECIFIER
_CONTRACTSPECIFIER_RIGHT.containing_type = _CONTRACTSPECIFIER
_DURATION.fields_by_name['unit'].enum_type = _DURATION_TIMEUNIT
_DURATION_TIMEUNIT.containing_type = _DURATION
_LOADHISTORICALDATAREQUEST.fields_by_name['contractSpecifier'].message_type = _CONTRACTSPECIFIER
_LOADHISTORICALDATAREQUEST.fields_by_name['duration'].message_type = _DURATION
_LOADHISTORICALDATAREQUEST.fields_by_name['barSize'].enum_type = _LOADHISTORICALDATAREQUEST_BARSIZE
_LOADHISTORICALDATAREQUEST.fields_by_name['barSource'].enum_type = _LOADHISTORICALDATAREQUEST_BARSOURCE
_LOADHISTORICALDATAREQUEST_BARSIZE.containing_type = _LOADHISTORICALDATAREQUEST
_LOADHISTORICALDATAREQUEST_BARSOURCE.containing_type = _LOADHISTORICALDATAREQUEST
DESCRIPTOR.message_types_by_name['ContractSpecifier'] = _CONTRACTSPECIFIER
DESCRIPTOR.message_types_by_name['Duration'] = _DURATION
DESCRIPTOR.message_types_by_name['LoadHistoricalDataRequest'] = _LOADHISTORICALDATAREQUEST
DESCRIPTOR.message_types_by_name['LoadHistoricalDataResponse'] = _LOADHISTORICALDATARESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ContractSpecifier = _reflection.GeneratedProtocolMessageType('ContractSpecifier', (_message.Message,), {
  'DESCRIPTOR' : _CONTRACTSPECIFIER,
  '__module__' : 'blotter.blotter_pb2'
  # @@protoc_insertion_point(class_scope:blotter.ContractSpecifier)
  })
_sym_db.RegisterMessage(ContractSpecifier)

Duration = _reflection.GeneratedProtocolMessageType('Duration', (_message.Message,), {
  'DESCRIPTOR' : _DURATION,
  '__module__' : 'blotter.blotter_pb2'
  # @@protoc_insertion_point(class_scope:blotter.Duration)
  })
_sym_db.RegisterMessage(Duration)

LoadHistoricalDataRequest = _reflection.GeneratedProtocolMessageType('LoadHistoricalDataRequest', (_message.Message,), {
  'DESCRIPTOR' : _LOADHISTORICALDATAREQUEST,
  '__module__' : 'blotter.blotter_pb2'
  # @@protoc_insertion_point(class_scope:blotter.LoadHistoricalDataRequest)
  })
_sym_db.RegisterMessage(LoadHistoricalDataRequest)

LoadHistoricalDataResponse = _reflection.GeneratedProtocolMessageType('LoadHistoricalDataResponse', (_message.Message,), {
  'DESCRIPTOR' : _LOADHISTORICALDATARESPONSE,
  '__module__' : 'blotter.blotter_pb2'
  # @@protoc_insertion_point(class_scope:blotter.LoadHistoricalDataResponse)
  })
_sym_db.RegisterMessage(LoadHistoricalDataResponse)



_BLOTTER = _descriptor.ServiceDescriptor(
  name='Blotter',
  full_name='blotter.Blotter',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=1765,
  serialized_end=1871,
  methods=[
  _descriptor.MethodDescriptor(
    name='LoadHistoricalData',
    full_name='blotter.Blotter.LoadHistoricalData',
    index=0,
    containing_service=None,
    input_type=_LOADHISTORICALDATAREQUEST,
    output_type=_LOADHISTORICALDATARESPONSE,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_BLOTTER)

DESCRIPTOR.services_by_name['Blotter'] = _BLOTTER

# @@protoc_insertion_point(module_scope)
