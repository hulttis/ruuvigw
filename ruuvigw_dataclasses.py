# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvigw_dataclasses.py
# Purpose:     ruuvigw dataclasses
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
from dataclasses import dataclass, field
from multiprocessing import Process, Queue
from asyncio import Task

# ==================================================================================
@dataclass
class procItem:
    proc: Process = None
    queue: Queue = None
    task: Task = None

# ==================================================================================
@dataclass
class procDict:
  procs: {procItem} = field(default_factory=dict)

  def add(self, key, proc: procItem):
    self.procs[key] = proc

  def get(self, key) -> procItem:
    if key in self.procs:
      return self.procs[key]
    return None

  def delete(self, key):
    if key in self.procs:
      del self.procs[key]
      return True
    return False

  def clear(self):
      self.procs.clear()





