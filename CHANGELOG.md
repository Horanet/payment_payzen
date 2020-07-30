# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- [Imp] Add PayZen status process and fields to show data from PayZen WebService

## [10.0.1.0.3] - 2019-03-08
### Added
- Change amount calculation to avoid rounding issues

## [10.0.1.0.2] - 2018-07-10
### Added
- [Fix #2] Find current acquirer from current transaction instead of load new acquirer recordset (can occur singleton errors on acquirer duplication)

## [10.0.1.0.1] - 2018-03-22
### Added
- Fill date_validate field of payment.transaction Odoo model on PayZen response (AUTHORISED or AUTHORISED_TO_VALIDATE)

## [10.0.1.0.0] - 2017-10-16
### Added
- Payzen payment acquirer module

[10.0.1.0.1]: https://github.com/Horanet/payment_payzen/compare/10.0.1.0.0...10.0.1.0.1
[10.0.1.0.2]: https://github.com/Horanet/payment_payzen/compare/10.0.1.0.1...10.0.1.0.2
[10.0.1.0.3]: https://github.com/Horanet/payment_payzen/compare/10.0.1.0.2...10.0.1.0.3
[Unreleased]: https://github.com/Horanet/payment_payzen/compare/10.0.1.0.3...HEAD