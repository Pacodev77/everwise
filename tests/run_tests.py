# tests/run_tests.py

import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import test_normalizacion

tests = [
    test_normalizacion.test_nuevo_sur_detalle_firma_b,
    test_normalizacion.test_san_agustin_asistencia_firma_a,
    test_normalizacion.test_misiones_asistencia_firma_a,
    test_normalizacion.test_misiones_detalle_firma_a,
    test_normalizacion.test_nuevo_sur_retardos_firma_c
]

passed_count = 0
failed_count = 0

print("Running attendance normalization tests...")
print("=========================================")

for t in tests:
    name = t.__name__
    print(f"Running {name}...", end=" ")
    sys.stdout.flush()
    try:
        t()
        print("PASSED")
        passed_count += 1
    except AssertionError as e:
        print("FAILED (AssertionError)")
        print(f"  Details: {e}")
        failed_count += 1
    except Exception as e:
        print("FAILED (Exception)")
        print(f"  Details: {e}")
        failed_count += 1

print("=========================================")
print(f"Result: {passed_count} PASSED, {failed_count} FAILED")

if failed_count > 0:
    sys.exit(1)
else:
    sys.exit(0)
