# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# automatically generated by the FlatBuffers compiler, do not modify

# namespace: tflite

import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class NonMaxSuppressionV5Options(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsNonMaxSuppressionV5Options(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = NonMaxSuppressionV5Options()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def NonMaxSuppressionV5OptionsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # NonMaxSuppressionV5Options
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

def NonMaxSuppressionV5OptionsStart(builder): builder.StartObject(0)
def NonMaxSuppressionV5OptionsEnd(builder): return builder.EndObject()


class NonMaxSuppressionV5OptionsT(object):

    # NonMaxSuppressionV5OptionsT
    def __init__(self):
        pass

    @classmethod
    def InitFromBuf(cls, buf, pos):
        nonMaxSuppressionV5Options = NonMaxSuppressionV5Options()
        nonMaxSuppressionV5Options.Init(buf, pos)
        return cls.InitFromObj(nonMaxSuppressionV5Options)

    @classmethod
    def InitFromObj(cls, nonMaxSuppressionV5Options):
        x = NonMaxSuppressionV5OptionsT()
        x._UnPack(nonMaxSuppressionV5Options)
        return x

    # NonMaxSuppressionV5OptionsT
    def _UnPack(self, nonMaxSuppressionV5Options):
        if nonMaxSuppressionV5Options is None:
            return

    # NonMaxSuppressionV5OptionsT
    def Pack(self, builder):
        NonMaxSuppressionV5OptionsStart(builder)
        nonMaxSuppressionV5Options = NonMaxSuppressionV5OptionsEnd(builder)
        return nonMaxSuppressionV5Options
