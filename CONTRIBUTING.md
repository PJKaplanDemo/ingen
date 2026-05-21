# Contributing to Interface Generator

Thank you for your interest in contributing to Interface Generator! We welcome all contributions, big or small. To ensure that contributions are properly tracked and attributed, we require that all contributors sign off on their work using the Developer Certificate of Origin (DCO).

## What is the Developer Certificate of Origin?

The Developer Certificate of Origin (DCO) is a lightweight way for contributors to certify that they wrote or otherwise have the right to submit the code they are contributing to the project. It is a simple statement that must be included in every Git commit message, indicating that the contributor accepts the DCO.

## How to Sign Off on Your Work

To sign off on your work, simply add the following line to the end of your Git commit message:

```bash
Signed-off-by: [Your Name] <[your email address]>
```

This indicates that you accept and agree to the DCO. You may include this line manually, or you can add it automatically by using the -s or --signoff option when committing:

```bash
git commit -s -m "Your commit message"
```

## Contributions without a Signed DCO

Contributions without a properly signed DCO cannot be accepted into the project. If you submit a contribution without a signed DCO, we will ask you to sign it before we can accept your contribution.

## Additional Resources

For more information about the Developer Certificate of Origin, please see the DCO 1.1 FAQ.

Thank you for your understanding and cooperation! We look forward to your contributions.

## Setting up this repository for development

- Clone the project locally:
  ```sh
  gh repo clone blackrock/ingen
  ```
- Create a Python virtual environment (Python 3.12 recommended):
  ```sh
  python -m venv venv
  source venv/bin/activate
  ```
- Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```

## Testing

- Ensure repository has at least **95%** code coverage. This is enforced automatically in CI via `--cov-fail-under=95`.
- Install `pytest`, `pytest-cov` and `coverage` via pip. Run the following command to check code coverage locally:
  ```sh
  pip install pytest pytest-cov coverage
  pytest test/ --cov=ingen --cov-fail-under=95 --cov-report= && coverage report -m
  ```