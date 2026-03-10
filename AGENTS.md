## MANDATORY: Use td for Task Management

You must run td usage --new-session at conversation start (or after /clear) to see current work.
Use td usage -q for subsequent reads.

## PXE Server Sync

After pushing changes to GitHub, always run `git pull` on the PXE server to keep it in sync:
```bash
ssh pxe "cd ~/repos/neuro; git pull origin main"
```

Also ensure .env file is preserved on PXE (it should be in .gitignore).
