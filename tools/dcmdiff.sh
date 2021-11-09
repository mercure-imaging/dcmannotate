#!/bin/bash

diff -a <(dcmdump $1) <(dcmdump $2)