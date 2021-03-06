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

class DensifyOptions(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsDensifyOptions(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = DensifyOptions()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def DensifyOptionsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # DensifyOptions
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

def DensifyOptionsStart(builder): builder.StartObject(0)
def DensifyOptionsEnd(builder): return builder.EndObject()


class DensifyOptionsT(object):

    # DensifyOptionsT
    def __init__(self):
        pass

    @classmethod
    def InitFromBuf(cls, buf, pos):
        densifyOptions = DensifyOptions()
        densifyOptions.Init(buf, pos)
        return cls.InitFromObj(densifyOptions)

    @classmethod
    def InitFromObj(cls, densifyOptions):
        x = DensifyOptionsT()
        x._UnPack(densifyOptions)
        return x

    # DensifyOptionsT
    def _UnPack(self, densifyOptions):
        if densifyOptions is None:
            return

    # DensifyOptionsT
    def Pack(self, builder):
        DensifyOptionsStart(builder)
        densifyOptions = DensifyOptionsEnd(builder)
        return densifyOptions
