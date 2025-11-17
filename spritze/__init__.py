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


from spritze.api.core import aresolve, init, resolve
from spritze.api.injection import inject
from spritze.api.provider import provider
from spritze.core.container import Container
from spritze.types import Depends, Scope

__all__ = (
    "Container",
    "Scope",
    "Depends",
    "provider",
    "inject",
    "resolve",
    "aresolve",
    "init",
)
