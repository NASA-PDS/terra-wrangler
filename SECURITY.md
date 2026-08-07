# Security Policy

## Supported Versions

terra-wrangler is a pre-1.0 developer-tooling project. Security fixes are only applied to the latest released version.

| Version | Supported |
|:--------|:---------:|
| 0.x     | ✅        |

## Reporting a Vulnerability

terra-wrangler has no runtime third-party dependencies and does not execute Terraform or hold AWS credentials — its blast radius is limited to false-positive/false-negative findings in a static text scan. That said, if you find a security issue (for example, a way the validator could be tricked into masking a real Must-Have violation, or an issue in the GitHub Actions workflows), please [submit an issue on our tracker](https://github.com/NASA-PDS/terra-wrangler/issues/new?template=vulnerability-issue.md).
