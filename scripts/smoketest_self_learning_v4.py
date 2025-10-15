# smoke import v4







try:







    from satpambot.bot.modules.discord_bot.cogs.self_learning_guard import SelfLearningGuard







    from satpambot.ml.guard_hooks import GuardAdvisor







    from satpambot.ml.online_nb import OnlineNB







    from satpambot.ml.state_store_discord import MLState







    from satpambot.ml.phash_reconcile import hamming_hex







    print("OK   : self-learning v4 import")







except Exception as e:







    print("FAILED self-learning v4:", e)







    raise SystemExit(1)







