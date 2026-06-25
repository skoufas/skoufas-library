"""Book management."""

default_app_config = "books.apps.BooksConfig"  # pylint: disable=invalid-name


def romanize(greek_text: str | None) -> str:
    """Return the ISO 843:1997 transcription of the input Greek text.
    Any non-Greek characters will be ignored and printed as they were.

    This function is (c) George Schizas, released under the Apache 2,0 licence
    See https://github.com/gschizas/RomanizePython/blob/master/src/romanize/romanize.py
    """

    if not greek_text:
        return ""
    result = ""
    cursor = 0
    while cursor < len(greek_text):
        letter = greek_text[cursor]
        prev_letter = greek_text[cursor - 1] if cursor > 0 else ""
        next_letter = greek_text[cursor + 1] if cursor < len(greek_text) - 1 else ""
        third_letter = greek_text[cursor + 2] if cursor < len(greek_text) - 2 else ""

        is_upper = letter.upper() == letter
        is_upper_next = next_letter.upper() == next_letter
        letter = letter.lower()
        prev_letter = prev_letter.lower()
        next_letter = next_letter.lower()
        third_letter = third_letter.lower()

        simple_translation_greek = "άβδέζήιίϊΐκλνξόπρσςτυύϋΰφωώ"
        simple_translation_latin = "avdeziiiiiklnxoprsstyyyyfoo"

        digraph_translation_greek = "θχψ"
        digraph_translation_latin = "thchps"

        digraph_ypsilon_greek = "αεη"
        digraph_ypsilon_latin = "aei"
        digraph_ypsilon_beta = "βγδζλμνραάεέηήιίϊΐοόυύϋΰωώ"
        digraph_ypsilon_phi = "θκξπστφχψ"

        if letter in simple_translation_greek:
            new_letter = simple_translation_latin[simple_translation_greek.index(letter)]
        elif letter in digraph_translation_greek:
            diphthong_index = digraph_translation_greek.index(letter)
            new_letter = digraph_translation_latin[diphthong_index * 2 : diphthong_index * 2 + 2]
        elif letter in digraph_ypsilon_greek:
            new_letter = digraph_ypsilon_latin[digraph_ypsilon_greek.index(letter)]
            if next_letter in ["υ", "ύ"]:
                if third_letter in digraph_ypsilon_beta:
                    new_letter += "v"
                    cursor += 1
                elif third_letter in digraph_ypsilon_phi:
                    new_letter += "f"
                    cursor += 1
        elif letter == "γ":
            if next_letter == "γ":
                new_letter = "ng"
                cursor += 1
            elif next_letter == "ξ":
                new_letter = "nx"
                cursor += 1
            elif next_letter in "χ":
                new_letter = "nch"
                cursor += 1
            else:
                new_letter = "g"
        elif letter == "μ":
            if next_letter == "π":
                if prev_letter.strip() == "" or third_letter.strip() == "":
                    new_letter = "b"
                    cursor += 1
                else:
                    new_letter = "mp"
                    cursor += 1
            else:
                new_letter = "m"
        elif letter == "ο":
            new_letter = "o"
            if next_letter in ["υ", "ύ"]:
                new_letter += "u"
                cursor += 1
        else:
            new_letter = letter
        if is_upper:
            new_letter = new_letter[0].upper() + (new_letter[1:].upper() if is_upper_next else new_letter[1:].lower())
        result += new_letter
        cursor += 1
    return result
