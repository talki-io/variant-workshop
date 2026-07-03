from app.compliance import scan_compliance


def test_pass_clean_text():
    r = scan_compliance("SAHM-X rilis laporan kuartal I, pendapatan segmen logistik naik.")
    assert r.status == "pass"
    assert r.banned_hits == []
    assert r.soft_flag_count == 0


def test_blocked_profit_guarantee():
    r = scan_compliance("Beli SAHM-X sekarang, dijamin untung dan pasti naik minggu depan!")
    assert r.status == "blocked"
    assert "dijamin untung" in r.banned_hits
    assert "pasti naik" in r.banned_hits


def test_blocked_insider():
    r = scan_compliance("Ini info orang dalam, bandar pasti naik.")
    assert r.status == "blocked"
    assert "info orang dalam" in r.banned_hits


def test_blocked_takes_priority_over_soft():
    # 同时含软提示与禁词 → 应判 blocked
    r = scan_compliance("Jangan sampai ketinggalan, dijamin cuan!")
    assert r.status == "blocked"


def test_soft_flag_returns_first_sentence_and_count():
    text = "SAHM-X menarik. Jangan sampai ketinggalan kereta. Institusi jelas sudah masuk."
    r = scan_compliance(text)
    assert r.status == "soft"
    assert r.soft_flag_count == 2
    assert "ketinggalan" in r.soft_flag_sentence.lower()


def test_soft_matches_mock_variant_sentence():
    # 对齐前端 mock v2 的 softFlagSentence
    r = scan_compliance("Sementara yang lain kejar rumor, SAHM-X udah catat laba. Siap-siap ketinggalan kayak kemarin?")
    assert r.status == "soft"
    assert r.soft_flag_count == 1


def test_case_insensitive():
    r = scan_compliance("PASTI UNTUNG kalau ikut sinyal ini")
    assert r.status == "blocked"
