/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 */

import { Component, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { Tenant } from '../models/tenant';
import { TenantsService } from '../tenants.service';

@Component({
  selector: 'app-list',
  templateUrl: './list.component.html',
  styleUrls: ['./list.component.scss'],
})
export class ListComponent implements OnInit {
  tenants$ = new Observable<Tenant[]>();
  tenantData: Tenant[] = [];
  isLoading: boolean = true;
  displayedColumns = [
    'tenantId',
    'tenantName',
    'tenantEmail',
    'tenantTier',
    'apiGatewayUrl',
    'isActive',
  ];
  constructor(private tenantSvc: TenantsService) {}

  ngOnInit(): void {

    let isValidUrl = (url: string) => {
      try {
        new URL(url)
        return true
     }catch(err){
        return false
      }
    }

    this.tenantSvc.fetch().subscribe((data) => {
      data.forEach((element) => {
        if(isValidUrl(element.apiGatewayUrl)){
          let url  = (new URL(element.apiGatewayUrl));
          element.apiGatewayUrl = url.protocol + '//' + url.hostname + '/';
        }   
      });
      this.tenantData = data;
      this.isLoading = false;
    });
  }
}
