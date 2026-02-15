SHELL := /usr/bin/env bash

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
LIBC_TOOLS := $(REPO_ROOT)/tools/libc

.PHONY: libc-init libc-patch-glibc libc-patch-musl libc-build-glibc libc-build-musl libc-build

libc-init:
	git submodule update --init lib/glibc lib/musl

libc-patch-glibc: libc-init
	$(LIBC_TOOLS)/apply-glibc-patches.sh

libc-patch-musl: libc-init
	$(LIBC_TOOLS)/apply-musl-patches.sh

libc-build-glibc: libc-patch-glibc
	$(LIBC_TOOLS)/build-glibc.sh

libc-build-musl: libc-patch-musl
	$(LIBC_TOOLS)/build-musl.sh

libc-build: libc-build-glibc libc-build-musl
