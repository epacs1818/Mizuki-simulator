from core import Ability, Hit, Combo, ActionCategory

aether_n1 = Ability("N1", hits=[Hit("N1_Hit", 0.000)])
aether_n1ca = Ability("Charged Attack", hits=[Hit("N1", 0.000), Hit("C1_Hit", 0.510), Hit("C2_Hit", 0.720)])
aether_skill = Ability(
    name="Elemental Skill",
    cooldown=15.0,
    hits=[
        Hit("Skill_Initial", 0.000, "1U", element="Cryo"),
        Hit("Skill_Proc1", 3.149, "1U", element="Cryo"),
        Hit("Skill_Proc2", 3.329),
        Hit("Skill_Proc3", 6.030, "1U", element="Cryo"),
        Hit("Skill_Proc4", 6.269),
        Hit("Skill_Proc5", 8.969, "1U", element="Cryo"),
        Hit("Skill_Proc6", 9.179),
        Hit("Skill_Proc7", 11.880, "1U", element="Cryo"),
        Hit("Skill_Proc8", 12.090),
        Hit("Skill_Proc9", 14.880, "1U", element="Cryo"),
        Hit("Skill_Proc10", 15.090),
    ]
)
aether_burst = Ability(
    name="Elemental Burst",
    cooldown=15.0,
    hits=[
        Hit("Burst_Cast", 0.000, "1U", element="Cryo"),
        Hit("Burst_Tick1", 0.550),
        Hit("Burst_Tick2", 0.550),
        Hit("Burst_Tick3", 0.660, "1U", element="Cryo"),
        Hit("Burst_Tick4", 0.780),
    ]
)
aether_ecq = Combo("AetherECQ", "Aether", swap_out_time=3.631)
aether_ecq.add_ability(0.601, aether_skill)
aether_ecq.add_ability(1.2, aether_n1ca)
aether_ecq.add_ability(3.061, aether_burst)

aether_en1 = Combo("AetherEN1", "Aether", swap_out_time=1.23)
aether_en1.add_ability(0.601, aether_skill)
aether_en1.add_ability(1.2, aether_n1)

aether_cq = Combo("AetherCQ", "Aether", swap_out_time=2.941)
aether_cq.add_ability(0.51, aether_n1ca)
aether_cq.add_ability(2.371, aether_burst)
