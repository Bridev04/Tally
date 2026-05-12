from pathlib import Path


MOBILE_ROOT = Path("mobile")


def read_mobile_source() -> str:
    source_files = [
        path
        for path in [*MOBILE_ROOT.glob("app/**/*.tsx"), *MOBILE_ROOT.glob("src/**/*.ts"), *MOBILE_ROOT.glob("src/**/*.tsx")]
        if path.is_file()
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in source_files)


def test_mobile_uses_secure_store_not_async_storage() -> None:
    source = read_mobile_source()

    assert "expo-secure-store" in source
    assert "SecureStore.setItemAsync" in source
    assert "SecureStore.deleteItemAsync" in source
    assert "AsyncStorage" not in source


def test_mobile_has_form_validation_and_safe_errors() -> None:
    source = read_mobile_source()

    assert "emailPattern" in source
    assert "Password must be at least 8 characters." in source
    assert "fallbackMessage" in source
    assert "console.log" not in source
    assert "console.error" not in source


def test_mobile_has_protected_navigation_and_logout() -> None:
    source = read_mobile_source()

    assert '<Redirect href="/(auth)/login"' in source
    assert '<Redirect href="/(app)"' in source
    assert "onPress={logout}" in source
