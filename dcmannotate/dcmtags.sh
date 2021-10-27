#!/bin/bash

dcmdump $1 | awk '{ print $(NF) }' 
