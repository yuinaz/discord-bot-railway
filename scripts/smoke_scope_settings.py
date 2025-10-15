from satpambot.config.runtime import cfg
print("== scope settings ==")
for k in ["LEARN_SCOPE","LEARN_WHITELIST_CHANNELS","LEARN_BLACKLIST_CHANNELS","LEARN_BLACKLIST_CATEGORIES",
          "LEARN_SCAN_PUBLIC_THREADS","LEARN_SCAN_PRIVATE_THREADS","LEARN_SCAN_FORUMS"]:
    print(k, "=", cfg(k))
print("OK")
