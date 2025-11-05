# Copyright 2025 Arseny Seliverstov
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from spritze.api.decorators import provider
from spritze.api.injection import aresolve, get_context, init, inject, resolve
from spritze.context import ContextField
from spritze.core.container import Container
from spritze.types import DependencyMarker, Depends, Scope

__all__ = [
    "Container",
    "Scope",
    "Depends",
    "DependencyMarker",
    "provider",
    "inject",
    "resolve",
    "aresolve",
    "init",
    "get_context",
    "ContextField",
]
