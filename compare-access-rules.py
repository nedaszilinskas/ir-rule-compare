#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import getopt
import hashlib
import xmlrpclib


class CompareAccessRules:

    def __init__(self, argv):
        try:
            opts, args = getopt.getopt(argv, 's:d:p:t:f:a:')
            assert len(argv) == 12
        except:
            self.usage()
            sys.exit()

        for opt, arg in opts:
            if opt == '-s':
                self.source_url = arg
            elif opt == '-d':
                self.source_db = arg
            elif opt == '-p':
                self.source_pwd = arg
            elif opt == '-t':
                self.target_url = arg
            elif opt == '-f':
                self.target_db = arg
            elif opt == '-a':
                self.target_pwd = arg
            else:
                self.usage()
                sys.exit()

        self.source_models = xmlrpclib.ServerProxy(
            '{}/xmlrpc/2/object'.format(self.source_url))
        self.target_models = xmlrpclib.ServerProxy(
            '{}/xmlrpc/2/object'.format(self.target_url))

    def usage(self):
        print "usage: python compate-access-rules.py -s <self.source_url>" +\
            " -d <self.source_db> -p <source_admin_password> -t" +\
            " <self.target_url> -f <self.target_db> -a <target_admin_password>"

    def compare(self):
        source = self.do_dict(self.source_models,
                              self.source_db, self.source_pwd)
        target = self.do_dict(self.target_models,
                              self.target_db, self.target_pwd)

        print "MISMATCH ON TARGET:\n"
        self.do_diff(source, target)

        print "\n\nMISMATCH ON SOURCE:\n"
        self.do_diff(target, source)

    def do_dict(self, models, db, pwd):

        models_xmlid_cache = {}
        groups_xmlid_cache = {}

        def get_model_xmlid_by_id(id):
            if str(id) in models_xmlid_cache:
                return models_xmlid_cache[str(id)]
            res = models.execute_kw(db, 1, pwd, 'ir.model.data', 'search_read',
                                    [
                                        [
                                            ['model', '=', 'ir.model'],
                                            ['res_id', '=', id]
                                        ]
                                    ])
            if not res:
                return str(id)
            xmlid = "%s.%s" % (res[0]['module'], res[0]['name'])
            models_xmlid_cache[str(id)] = xmlid
            return xmlid

        def get_group_xmlid_by_id(id):
            if str(id) in groups_xmlid_cache:
                return groups_xmlid_cache[str(id)]
            res = models.execute_kw(db, 1, pwd, 'ir.model.data', 'search_read',
                                    [
                                        [
                                            ['model', '=', 'res.groups'],
                                            ['res_id', '=', id]
                                        ]
                                    ])
            if not res:
                return str(id)
            xmlid = "%s.%s" % (res[0]['module'], res[0]['name'])
            groups_xmlid_cache[str(id)] = xmlid
            return xmlid

        rules = models.execute_kw(db, 1, pwd, 'ir.rule', 'search_read', [])
        dtc = {}
        for r in rules:
            groups = []
            for id in r['groups']:
                groups.append(get_group_xmlid_by_id(id))
            model_xmlid = get_model_xmlid_by_id(r['model_id'][0])
            hash_values = str(r['domain_force']).strip().replace(" ", "") +\
                str(r['active']) +\
                str(model_xmlid) +\
                str(r['global']) +\
                str(groups) +\
                str(r['perm_read']) +\
                str(r['perm_write']) +\
                str(r['perm_create']) +\
                str(r['perm_unlink'])
            hashname = hashlib.md5(hash_values).hexdigest()
            dtc[hashname] = {
                'id': r['id'],
                'active': r['active'],
                'name': r['name'],
                'domain_force': r['domain_force'],
                'model': r['model_id'],
                'global': r['global'],
                'groups': groups,
                'model_xmlid': model_xmlid,
                'perm_read': r['perm_read'],
                'perm_write': r['perm_write'],
                'perm_create': r['perm_create'],
                'perm_unlink': r['perm_unlink'],
            }

        return dtc

    def do_diff(self, l1, l2):
        diff = set(l1.keys()) - set(l2.keys())
        for hashname in diff:
            print "%s (ID: %s)" % (
                l1[hashname]['name'],
                l1[hashname]['id']
            )
            print "active: ", l1[hashname]['active']
            print "model_xmlid: ", l1[hashname]['model_xmlid']
            print "domain_force: ", l1[hashname]['domain_force']
            print "groups: ", l1[hashname]['groups']
            print "perm_read: ", l1[hashname]['perm_read']
            print "perm_write: ", l1[hashname]['perm_write']
            print "perm_create: ", l1[hashname]['perm_create']
            print "perm_unlink: ", l1[hashname]['perm_unlink']
            print "___________________"


if __name__ == "__main__":
    CompareAccessRules(sys.argv[1:]).compare()
