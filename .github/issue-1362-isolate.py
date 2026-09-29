"""Validate the unchanged nonce module despite unrelated workspace blockers.

The fixture preserves nonce.rs and its ten module-level tests verbatim. It
supplies only the original Nonce storage-key shape and the three exact numeric
error constants those helpers use. The three public-entrypoint tests are NOT
executed here; normal crate execution remains blocked and must be disclosed.
"""
from pathlib import Path
import re

source = Path('contracts/credence_delegation/src')
root = Path('/tmp/issue-1362-isolated')
(root / 'src').mkdir(parents=True, exist_ok=True)
(root / 'errors/src').mkdir(parents=True, exist_ok=True)
errors = Path('contracts/credence_errors/src/lib.rs').read_text()
codes = {}
for name in ['InvalidNonce', 'Overflow', 'Underflow']:
    matches = re.findall(rf'\b{name}\s*=\s*(\d+)\s*,', errors)
    assert len(matches) == 1, (name, matches)
    codes[name] = matches[0]
lib = source.joinpath('lib.rs').read_text()
span = re.search(r'pub const MAX_NONCE_INVALIDATION_SPAN: u64 = ([\d_]+);', lib).group(1)
root.joinpath('Cargo.toml').write_text('''[package]
name = "nonce-isolated-validation"
version = "0.0.0"
edition = "2021"
[workspace]
members = ["errors"]
[dependencies]
soroban-sdk = "=22.0.11"
credence_errors = { path = "errors" }
[dev-dependencies]
soroban-sdk = { version = "=22.0.11", features = ["testutils"] }
[profile.dev]
debug = 0
[profile.test]
debug = 0
''')
root.joinpath('errors/Cargo.toml').write_text('''[package]
name = "credence_errors"
version = "0.0.0"
edition = "2021"
[dependencies]
soroban-sdk = "=22.0.11"
''')
root.joinpath('errors/src/lib.rs').write_text('''#![no_std]
use soroban_sdk::contracterror;
#[contracterror(export = false)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u32)]
pub enum ContractError {
''' + ''.join(f'    {name} = {value},\n' for name, value in codes.items()) + '}\n')
root.joinpath('src/lib.rs').write_text('''#![no_std]
use soroban_sdk::{contracttype, Address};
#[contracttype]
#[derive(Clone)]
pub enum DataKey { Nonce(Address) }
pub mod nonce;
''')
root.joinpath('src/nonce.rs').write_text(source.joinpath('nonce.rs').read_text())
tests = source.joinpath('test_nonce_boundaries.rs').read_text()
tests = tests[:tests.index('#[test]\nfn downstream_failure_')]
tests = re.sub(r'use crate::\{.*?\};', f'const MAX_NONCE_INVALIDATION_SPAN: u64 = {span};', tests, count=1, flags=re.S)
start = tests.index('fn public_setup()')
end = tests.index('\n#[test]', start)
tests = tests[:start] + tests[end:]
root.joinpath('src/test_nonce_boundaries.rs').write_text(tests)
print('Isolated module fixture:', root)
print('Original wire codes:', codes, 'invalidation span:', span)
