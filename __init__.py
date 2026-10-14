# -*- coding: utf-8 -*-
def classFactory(iface):
    from .VectorClassManager import VectorClassManager
    return VectorClassManager(iface)
