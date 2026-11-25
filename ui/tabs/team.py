"""Tab 1: team, gear and weapon configuration."""

import streamlit as st

from build_io import SUBSTAT_STANDARDS, assemble_party
from substats_standards import CARRIES, standard_piece_mains
from ui.build_panel import render_build_io_panel
from ui.cards import render_character_cards, validate_talents
from ui.constants import (CHARACTERS, LEVEL_OPTIONS, CHARACTER_WEAPONS,
                          CHARACTER_CONSTELLATIONS, CHARACTER_ARTIFACT_SETS,
                          SANDS_MAINS, GOBLET_MAINS, CIRCLET_MAINS,
                          SUBSTAT_OPTIONS)
from ui.state import go_to_enemy_tab, invalidate_last_run


def render() -> None:
    team_data = {}

    render_build_io_panel()

    st.subheader("1. Team, Characters and Weapon Configuration")

    # Placeholder for the party cards: they are drawn HERE, right under the section
    # header, but they are FILLED at the bottom of the tab — after "Confirm party
    # configuration" has rebuilt the party — so they always show the current party.
    cards_slot = st.container()

    cols = st.columns(4)

    current_selections = {}
    for s in range(1, 5):
        val = st.session_state.get(f"char_{s}")
        if val and val != "Select Character":
            current_selections[s] = val

    for i, col in enumerate(cols):
        slot_num = i + 1
        with col:
            st.markdown(f"### Slot {slot_num}")
            
            chosen_in_other_slots = {char_val for s, char_val in current_selections.items() if s != slot_num}
            slot_char_options = [c for c in CHARACTERS if c == "Select Character" or c not in chosen_in_other_slots]
            
            curr_char = st.session_state.get(f"char_{slot_num}", "Select Character")
            if curr_char not in slot_char_options:
                curr_char = "Select Character"
                st.session_state[f"char_{slot_num}"] = "Select Character"
                
            char_idx = slot_char_options.index(curr_char)
            char = st.selectbox("Character", slot_char_options, index=char_idx, key=f"char_{slot_num}")

            # Level defaults to 90
            curr_lv = st.session_state.get(f"level_{slot_num}", 90)
            lv_idx = LEVEL_OPTIONS.index(curr_lv) if curr_lv in LEVEL_OPTIONS else LEVEL_OPTIONS.index(90)
            char_level = st.selectbox("Level", LEVEL_OPTIONS, index=lv_idx, key=f"level_{slot_num}")

            # Constellations (driven by CHARACTER_CONSTELLATIONS dictionary)
            const_options = CHARACTER_CONSTELLATIONS.get(char, ["C0"])
            if f"const_{slot_num}" in st.session_state and st.session_state[f"const_{slot_num}"] not in const_options:
                st.session_state[f"const_{slot_num}"] = const_options[0]
            const = st.selectbox("Constellation", const_options, key=f"const_{slot_num}")
                
            # Weapon & Refinement
            if char in CHARACTER_WEAPONS:
                available_weapons_list = CHARACTER_WEAPONS[char]
                weapon_names = [w[0] for w in available_weapons_list]
                
                if f"weapon_{slot_num}" in st.session_state and st.session_state[f"weapon_{slot_num}"] not in weapon_names:
                    st.session_state[f"weapon_{slot_num}"] = weapon_names[0]
                    
                chosen_weapon = st.selectbox("Weapon", weapon_names, key=f"weapon_{slot_num}")
                valid_refines = [w[1] for w in available_weapons_list if w[0] == chosen_weapon][0]
                
                refine_options = [f"R{r}" for r in valid_refines]
                if f"ref_{slot_num}" in st.session_state and st.session_state[f"ref_{slot_num}"] not in refine_options:
                    st.session_state[f"ref_{slot_num}"] = refine_options[0]
                refine_choice = st.selectbox("Refinement", refine_options, key=f"ref_{slot_num}")
                refinement_val = int(refine_choice.replace("R", ""))
            else:
                chosen_weapon = "Select Weapon"
                st.selectbox("Weapon", ["Select Weapon"], key=f"weapon_locked_{slot_num}", disabled=True)
                refinement_val = 1
                st.selectbox("Refinement", ["R1"], key=f"ref_locked_{slot_num}", disabled=True)

            talent_input = st.text_input(
                "Talent Levels",
                placeholder="10/13/13",
                key=f"talents_{slot_num}"
            )
                
            team_data[f"Slot {slot_num}"] = {
                "character": char,
                "level": char_level,
                "constellation": const,
                "weapon": chosen_weapon,
                "refinement": refinement_val,
                "talents": talent_input.strip() if talent_input else "",
                "artifacts": {}
            }
    
    st.markdown("---")

    # Artifacts Entry Section
    st.subheader("2. Artifact Sets & Piece Stats")
    st.write("Configure the set bonus, main stats, and substats for each piece.")

    for slot_num in range(1, 5):
        char_name = team_data[f"Slot {slot_num}"]["character"]
        label_name = char_name if char_name != "Select Character" else f"Character {slot_num}"
        
        with st.expander(f"Artifacts for {label_name} (Slot {slot_num})", expanded=False):
            set_options = CHARACTER_ARTIFACT_SETS.get(char_name, ["Select Set"])
                
            if f"art_set_{slot_num}" in st.session_state and st.session_state[f"art_set_{slot_num}"] not in set_options:
                st.session_state[f"art_set_{slot_num}"] = set_options[0]

            selected_set = st.selectbox(
                f"Main Artifact Set for {label_name}",
                set_options,
                key=f"art_set_{slot_num}"
            )

            # Substat standard selector. Every character gets the radio so the
            # layout is uniform, but only carries have RV / KQM standards: a
            # support's radio is locked to "Manual" and explained below. The
            # options are mutually exclusive by construction: RV and KQM both
            # lock mains AND substats, because neither matters once a standard
            # is selected.
            is_carry = char_name in CARRIES
            standard_options = list(SUBSTAT_STANDARDS) if is_carry else ["Manual"]
            # A slot that used to hold a carry may still have "KQM ..." stored in
            # session state, which is not a valid option for a support -> reset.
            if st.session_state.get(f"std_{slot_num}") not in standard_options:
                st.session_state[f"std_{slot_num}"] = "Manual"
            standard_mode = st.radio(
                "Substat standard",
                options=standard_options,
                index=0,
                horizontal=True,
                key=f"std_{slot_num}",
                disabled=not is_carry,
                help=("RV/KQM lock mains + substats and model crit as a single "
                      "Crit Value (CV)." if is_carry else None),
            )
            if not is_carry and char_name != "Select Character":
                st.caption("Manual mode only. No standards built for this character")

            crit_value_mode = False
            crit_rate_locked = False
            locked_mains = None
            if standard_mode != "Manual":
                locked_mains = standard_piece_mains(char_name)
            else:
                # Manual-mode crit switches, offered to carries AND supports.
                # "Crit Value units" hands the crit to the CV model, which is
                # deterministic, so the 100% Crit Rate lock is not offered
                # alongside it.
                crit_value_mode = st.toggle(
                    "Crit Value units",
                    key=f"cv_{slot_num}",
                    help="Enter crit as Crit Value (CV = 2*CR + CD) and let the "
                         "engine use the CV formula.",
                )
                if crit_value_mode:
                    # The lock is meaningless under the CV model, so keep the
                    # widget honest: switch it off before it is drawn.
                    st.session_state[f"crlock_{slot_num}"] = False
                crit_rate_locked = st.toggle(
                    "100% Crit Rate",
                    key=f"crlock_{slot_num}",
                    disabled=crit_value_mode,
                    help="Every hit counts as a crit. Not available with Crit Value units.",
                )
            subs_locked = standard_mode != "Manual"
            mains_locked = subs_locked
            slot_data = team_data[f"Slot {slot_num}"]
            slot_data["standard_mode"] = standard_mode
            slot_data["crit_value_mode"] = crit_value_mode
            slot_data["crit_rate_locked"] = crit_rate_locked

            st.markdown("")
            pieces_data = {}
            f_col, fe_col, s_col, g_col, c_col = st.columns(5)
            
            def render_piece_inputs(piece_name, main_stat_widget, disable_subs=False, locked_main=None):
                st.markdown(f"**{piece_name}**")
                
                if main_stat_widget == "locked_hp":
                    st.text_input("Main Stat", value="Flat HP", key=f"main_{piece_name}_{slot_num}", disabled=True)
                    main_stat = "Flat HP"
                elif main_stat_widget == "locked_atk":
                    st.text_input("Main Stat", value="Flat ATK", key=f"main_{piece_name}_{slot_num}", disabled=True)
                    main_stat = "Flat ATK"
                elif locked_main is not None:
                    st.text_input("Main Stat", value=locked_main, key=f"main_locked_{piece_name}_{slot_num}", disabled=True)
                    main_stat = locked_main
                else:
                    main_stat = st.selectbox("Main Stat", main_stat_widget, key=f"main_{piece_name}_{slot_num}")

                rarity = st.radio(
                    "Artifact Rarity",
                    options=["5★", "4★"],
                    index=0,
                    horizontal=True,
                    key=(f"rarity_locked_{piece_name}_{slot_num}" if disable_subs else f"rarity_{piece_name}_{slot_num}"),
                    disabled=disable_subs,
                )
                    
                st.markdown("---")
                st.caption("Substats")
                
                substats_list = []
                for sub_idx in range(1, 5):
                    sub_col1, sub_col2, sub_col3 = st.columns([1.4, 1.1, 0.3], vertical_alignment="center")
                    with sub_col1:
                        sub_type = st.selectbox(
                            f"Sub {sub_idx}", 
                            SUBSTAT_OPTIONS, 
                            key=f"sub_type_{piece_name}_{slot_num}_{sub_idx}",
                            label_visibility="collapsed",
                            disabled=disable_subs
                        )
                    is_pct = "%" in sub_type
                    placeholder = ("CV pts" if sub_type == "Crit Value"
                                   else "%" if is_pct else "Value")
                    with sub_col2:
                        sub_val = st.text_input(
                            f"Val {sub_idx}", 
                            placeholder=placeholder, 
                            key=f"sub_val_{piece_name}_{slot_num}_{sub_idx}",
                            label_visibility="collapsed",
                            disabled=disable_subs
                        )
                    with sub_col3:
                        if is_pct:
                            st.markdown("**%**")

                    if not disable_subs and sub_type != "None":
                        substats_list.append({"stat": sub_type, "value": sub_val})
                        
                return {
                    "main_stat": main_stat,
                    "rarity": rarity,
                    "substats": substats_list
                }

            with f_col:
                pieces_data["Flower"] = render_piece_inputs("Flower", "locked_hp", disable_subs=subs_locked, locked_main=(locked_mains["Flower"] if locked_mains else None))
            with fe_col:
                pieces_data["Feather"] = render_piece_inputs("Feather", "locked_atk", disable_subs=subs_locked, locked_main=(locked_mains["Feather"] if locked_mains else None))
            with s_col:
                pieces_data["Sands"] = render_piece_inputs("Sands", SANDS_MAINS, disable_subs=subs_locked, locked_main=(locked_mains["Sands"] if locked_mains else None))
            with g_col:
                pieces_data["Goblet"] = render_piece_inputs("Goblet", GOBLET_MAINS, disable_subs=subs_locked, locked_main=(locked_mains["Goblet"] if locked_mains else None))
            with c_col:
                pieces_data["Circlet"] = render_piece_inputs("Circlet", CIRCLET_MAINS, disable_subs=subs_locked, locked_main=(locked_mains["Circlet"] if locked_mains else None))
                
            team_data[f"Slot {slot_num}"]["artifacts"] = {
                "Set": selected_set,
                "Pieces": pieces_data
            }

    
    # Build a signature of current team inputs to detect changes. It must cover EVERY
    # input that feeds the party stats - gear (mains / rarity / substats) and the
    # substat standard included - otherwise editing them leaves the previously
    # confirmed party in place and the app silently keeps simulating the old build.
    current_signature = []
    for s_num in range(1, 5):
        sd = team_data[f"Slot {s_num}"]
        pieces = (sd.get("artifacts") or {}).get("Pieces") or {}
        gear_signature = tuple(
            (
                piece,
                (pieces.get(piece) or {}).get("main_stat"),
                (pieces.get(piece) or {}).get("rarity"),
                tuple(
                    ((sub or {}).get("stat"), str((sub or {}).get("value") or ""))
                    for sub in ((pieces.get(piece) or {}).get("substats") or [])
                ),
            )
            for piece in ("Flower", "Feather", "Sands", "Goblet", "Circlet")
        )
        current_signature.append((
            sd["character"], sd["level"], sd["constellation"],
            sd["weapon"], sd["refinement"], sd["talents"],
            sd.get("artifacts", {}).get("Set"),
            sd.get("standard_mode", "Manual"),
            sd.get("crit_value_mode", False),
            sd.get("crit_rate_locked", False),
            gear_signature,
        ))
    
    # If settings changed since last party creation, the confirmed party is stale: hide
    # it and mark the newest inputs as not processed yet (which also drops a stale
    # "Trial simulation complete!" from the last run).
    dirty = ("last_team_signature" in st.session_state
             and st.session_state["last_team_signature"] != current_signature)
    if dirty:
        st.session_state["party_created"] = False
        invalidate_last_run()
    warn_slot = st.empty()   # filled after the button, so a confirming click can skip it

    confirmed_now = False


    # Button renamed and validation relaxed to ONLY require characters
    if st.button("Confirm party configuration", type="primary"):
        has_empty_characters = False
        for slot_num in range(1, 5):
            s_data = team_data[f"Slot {slot_num}"]
            c = s_data["character"]
            
            # Only check if character selection is empty / default
            if not c or c == "Select Character":
                has_empty_characters = True
                break

        if has_empty_characters:
            st.session_state["party_created"] = False
            st.error("Please select characters for all slots.")
        else:
            talent_errors = []
            parsed_talents = {}
            for slot_num in range(1, 5):
                s_data = team_data[f"Slot {slot_num}"]
                c = s_data["character"]
                t = s_data["talents"]
                
                # If talents are left empty, default them or validate
                if not t:
                    parsed_talents[slot_num] = [1, 1, 1] # Safe default if skipped
                else:
                    is_valid, err_msg, levels = validate_talents(t)
                    if not is_valid:
                        talent_errors.append(f"Slot {slot_num} ({c}): {err_msg}")
                    else:
                        parsed_talents[slot_num] = levels
                    
            if talent_errors:
                st.session_state["party_created"] = False
                for err in talent_errors:
                    st.error(f"Format error: {err}")
            else:
                slot_specs = []
                for slot_num in range(1, 5):
                    data = team_data[f"Slot {slot_num}"]
                    if data["character"] == "Select Character":
                        continue  # Skip empty slots if any slip through
                    slot_specs.append({
                        "character": data["character"],
                        "level": data.get("level", 90),
                        "constellation": data.get("constellation", "C0"),
                        "weapon": data["weapon"],
                        "refinement": data["refinement"],
                        "talents": data["talents"],
                        "talent_levels": parsed_talents[slot_num],
                        "artifact_set": data.get("artifacts", {}).get("Set", "Select Set"),
                        "standard_mode": (data.get("standard_mode", "Manual")
                                          if data["character"] in CARRIES else "Manual"),
                        "crit_value_mode": data.get("crit_value_mode", False),
                        "crit_rate_locked": data.get("crit_rate_locked", False),
                        "pieces": data.get("artifacts", {}).get("Pieces", {}),
                    })

                # Gear -> stat pools lives in build_io, so a party restored from a file
                # is built by exactly the same code as one typed in here.
                st.session_state["my_party"] = assemble_party(slot_specs)
                st.session_state["party_created"] = True
                st.session_state["last_team_signature"] = current_signature
                confirmed_now = True
                st.success("Party successfully created!")

    # Warn ONLY while the inputs are genuinely unconfirmed: on the click that confirms
    # them, the success message above replaces the warning instead of stacking with it.
    if dirty and not confirmed_now:
        warn_slot.warning(
            "Gear, substats or the substat standard changed since the party was "
            "confirmed — press **Confirm party configuration** to rebuild it. "
            "(Running a trial always uses the current inputs.)"
        )

    # Party cards are written into the placeholder created under the section header,
    # so they appear at the top of the tab while still reflecting this run's party.
    if st.session_state.get("party_created") and st.session_state.get("my_party"):
        with cards_slot:
            render_character_cards(st.session_state["my_party"])

        st.markdown("---")
        col_proceed1, col_proceed2, col_proceed3 = st.columns([1, 2, 1])
        with col_proceed2:
            st.button(
                "Proceed to Enemy Configuration",
                type="primary",
                use_container_width=True,
                on_click=go_to_enemy_tab
            )
