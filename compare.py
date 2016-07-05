#!/usr/bin/python
# -*- coding: utf-8 -*-
import configparser
import os
import sys
import getopt
import hashlib
import xmlrpclib


class CompareAccessRules:

    def __init__(self, argv):
        try:
            opts, args = getopt.getopt(argv, 'c:')
            assert len(argv) == 2
        except:
            self.usage()
            sys.exit()

        for opt, arg in opts:
            if opt == '-c':
                config_path = arg
            else:
                self.usage()
                sys.exit()

        assert os.path.isfile(config_path), "Config file not found!"
        config = configparser.ConfigParser()
        config.read(config_path)

        ls_url = config.get('LEFT_SERVER', 'url')
        ls_db = config.get('LEFT_SERVER', 'database')
        ls_password = config.get('LEFT_SERVER', 'admin_password')
        assert ls_url, "Left server url not defined!"
        assert ls_db, "Left server database not defined!"
        assert ls_password, "Left server admoin password not defined!"

        rs_url = config.get('RIGHT_SERVER', 'url')
        rs_db = config.get('RIGHT_SERVER', 'database')
        rs_password = config.get('RIGHT_SERVER', 'admin_password')
        assert rs_url, "Right server url not defined!"
        assert rs_db, "Right server db not defined!"
        assert rs_password, "Right server admin password not defined!"

        self.common_model = config.get('COMMON', 'model')
        assert self.common_model, "Model not defined!"
        common_fields = config.get('COMMON', 'fields')
        assert common_fields, "Fields not defined!"
        self.common_fields = []
        for field in common_fields.split(','):
            if field.find('/') != -1:
                split = field.split('/')
                self.common_fields.append([split[0], split[1]])
            else:
                self.common_fields.append(field)
        self.common_domain = eval(config.get('COMMON', 'domain'))
        self.common_context = eval(config.get('COMMON', 'context'))

        left_models = xmlrpclib.ServerProxy(
            '{}/xmlrpc/2/object'.format(ls_url))
        right_models = xmlrpclib.ServerProxy(
            '{}/xmlrpc/2/object'.format(rs_url))

        left = self.do_dict(
            left_models,
            ls_db,
            ls_password,
        )
        right = self.do_dict(
            right_models,
            rs_db,
            rs_password,
        )

        print "MISMATCH ON RIGHT:\n"
        self.do_diff(left, right)

        print "\n\nMISMATCH ON LEFT:\n"
        self.do_diff(right, left)

    def usage(self):
        print "usage: python compare-records.py -c <config_path>"

    def do_dict(self, models, db, pwd):

        xmlid_cache = {}

        def get_xmlid_by_id(realted_model, id):
            if realted_model in xmlid_cache \
                    and str(id) in xmlid_cache[realted_model]:
                return xmlid_cache[realted_model][str(id)]

            res = models.execute_kw(
                db,
                1,
                pwd,
                'ir.model.data',
                'search_read',
                [
                    [
                        ['model', '=', realted_model],
                        ['res_id', '=', id]
                    ]
                ])

            if not res:
                return str(id)

            xmlid = "%s.%s" % (res[0]['module'], res[0]['name'])
            if realted_model not in xmlid_cache:
                xmlid_cache[realted_model] = {}
            xmlid_cache[realted_model][str(id)] = xmlid
            return xmlid

        domain = []
        domain.append(self.common_domain)

        records = models.execute_kw(
            db,
            1,
            pwd,
            self.common_model,
            'search_read',
            domain,
            {'context': self.common_context},
        )

        dtc = {}
        for r in records:
            hash_values = []
            for f in self.common_fields:
                if isinstance(f, list):
                    vals = []
                    if f[1] in r and r[f[1]]:
                        if all(isinstance(x, int) for x in r[f[1]]):
                            for id in r[f[1]]:
                                vals.append(get_xmlid_by_id(f[0], id))
                        else:
                            vals.append(get_xmlid_by_id(f[0], r[f[1]][0]))
                        hash_values.append(','.join(vals))
                    else:
                        hash_values.append('False')
                elif isinstance(f, basestring):
                    hash_values.append(str(r[f]).strip().replace(" ", ""))

            hash_values = ','.join(hash_values)
            hashname = hashlib.md5(hash_values).hexdigest()

            dtc[hashname] = {
                "id": r['id'],
                "name": r['name'],
                "hashed_string": hash_values,
            }

        return dtc

    def do_diff(self, l1, l2):
        diff = set(l1.keys()) - set(l2.keys())
        for hashname in diff:
            print "%s (ID: %s)\n%s\n\n" % (
                l1[hashname]['name'],
                l1[hashname]['id'],
                "",  # l1[hashname]['hashed_string'],
            )

if __name__ == "__main__":
    CompareAccessRules(sys.argv[1:])
