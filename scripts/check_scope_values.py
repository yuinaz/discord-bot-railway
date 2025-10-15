from satpambot.config.runtime import cfg
from satpambot.config.local_cfg import cfg as mcfg
print("== runtime.cfg ==")
for k in ["LEARN_SCOPE","LEARN_BLACKLIST_CHANNELS","LEARN_BLACKLIST_CATEGORIES",
          "LEARN_SCAN_PUBLIC_THREADS","LEARN_SCAN_PRIVATE_THREADS","LEARN_SCAN_FORUMS"]:
    print(k, "=", cfg(k))
print("\n== module_options/local_cfg (mcfg) ==")
for k in ["LEARN_SCOPE","LEARN_BLACKLIST_CHANNELS","LEARN_BLACKLIST_CATEGORIES",
          "LEARN_SCAN_PUBLIC_THREADS","LEARN_SCAN_PRIVATE_THREADS","LEARN_SCAN_FORUMS"]:
    print(k, "=", mcfg(k))
