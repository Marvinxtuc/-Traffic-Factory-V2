# Security Policy

## Supported Versions

Traffic Factory V2 is currently in an early development phase.

Security fixes are applied to the default branch:

```text
main
```

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.

If you believe you have found a vulnerability, please contact the maintainer
privately through GitHub profile contact channels.

If private contact is not available, you may open a minimal public issue that
states a security concern exists without disclosing exploit details, payloads,
private data, or reproduction steps that could be abused.

When reporting a vulnerability, please include:

- A clear summary of the issue
- Affected files or components
- Steps to reproduce, if safe to share privately
- Potential impact
- Whether the issue involves secrets, workflow gates, persistence, provider
  adapters, file handling, runtime exposure, or release checks

## Security Scope

Security-sensitive areas include:

1. Workflow gate bypass
2. Publish check bypass
3. SQLite persistence corruption
4. Unsafe provider adapter behavior
5. Secret, token, credential, or runtime data leakage
6. CI or release-check bypass
7. Unsafe file handling
8. Unexpected network exposure
9. Runtime database exposure
10. Insecure handling of logs or generated artifacts

## Secrets and Credentials

Do not commit:

- API keys
- Access tokens
- Private credentials
- Production database files
- Runtime logs containing sensitive data
- Private customer, operator, or source data
- Unredacted screenshots containing tokens or private information

Use local environment files or ignored runtime configuration instead.

## Responsible Disclosure

The maintainer will review valid reports and prioritize fixes based on severity,
exploitability, and project impact.

Security reports that include safe reproduction steps, impact analysis, and
affected components are easier to triage and resolve.
