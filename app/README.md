# App

Angular 21 frontend application.

## Prerequisites

- [Bun](https://bun.sh/) (package manager)
- Node.js 22.12+

## Installation

```bash
bun install
```

## Development

Start the development server:

```bash
bun run start
```

The app will be available at `http://localhost:4200/`. It automatically reloads on file changes.

## Building

```bash
bun run build
```

Build artifacts are output to `dist/app/`.

## Linting

```bash
bun run lint
```

To auto-fix issues:

```bash
bun run lint -- --fix
```

## Code Scaffolding

Generate components, services, etc.:

```bash
bunx ng generate component component-name
bunx ng generate service service-name
```

For all available schematics:

```bash
bunx ng generate --help
```
