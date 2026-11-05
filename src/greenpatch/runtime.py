"""Domain selection for scripts. Import and call `domain_from_argv()` BEFORE importing greenpatch.config.

    from greenpatch.runtime import add_domain_arg, domain_from_argv
    domain_from_argv()                  # reads --domain X from sys.argv -> GREENPATCH_DOMAIN
    from greenpatch import config       # now uses the chosen domain
    ...
    add_domain_arg(ap)                  # so --domain shows in --help and argparse accepts it
"""
import os
import sys

DOMAIN_CHOICES = ("pilot", "full")   # keys of config.DOMAINS (not imported here: config reads the variable)


def domain_from_argv(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for i, arg in enumerate(argv):
        if arg == "--domain" and i + 1 < len(argv):
            os.environ["GREENPATCH_DOMAIN"] = argv[i + 1]
        elif arg.startswith("--domain="):
            os.environ["GREENPATCH_DOMAIN"] = arg.split("=", 1)[1]


def add_domain_arg(ap):
    ap.add_argument("--domain", choices=DOMAIN_CHOICES,
                    help="analysis domain (default: $GREENPATCH_DOMAIN, else 'pilot')")
